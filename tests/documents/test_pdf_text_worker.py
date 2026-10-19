"""窄页worker的句柄关闭、同线程顺序及真实隔离进程验证。"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import multiprocessing
import os
from pathlib import Path
import threading
import time
from typing import cast

import pytest

from dayu.contracts.json_value import JsonValue
from dayu.documents.pdf_text_worker import PdfTextWorker
from dayu.fins.pipelines.hk_body_extraction import extract_hk_pages, extract_hk_pages_async, HkBodyExtractionError, _decode
from dayu.fins.pipelines.cn_download_models import CnDownloadCancelledError
from dayu.runtime.interruptible_process import InterruptibleProcessHandle, InterruptibleProcessFailed, InterruptibleProcessCompleted
from tests.fins.test_hk_body_period import official_inputs
import dayu.documents.pdf_text_worker as worker
import dayu.fins.pipelines.hk_body_extraction as extraction


class _Native:
    """记录所有native操作的单一线程与关闭顺序的合成边界。"""
    def __init__(self, log: list[tuple[str,int]], fail: str) -> None:
        """参数：log/fail。返回：无。异常：无。"""
        self.log, self.fail, self.role = log,fail,'document'
    def PdfDocument(self, input: bytes) -> '_Native':
        """参数：原件。返回：文档。异常：指定打开故障。"""
        self.record('open')
        if self.fail=='open':raise ValueError('synthetic open')
        return self
    def __len__(self) -> int:
        """参数：无。返回：两页。异常：无。"""
        self.record('length');return 2
    def __getitem__(self,index: int) -> '_Native':
        """参数：页序号。返回：页面。异常：无。"""
        self.record('page');page=_Native(self.log,self.fail);page.role='page';return page
    def get_textpage(self) -> '_Native':
        """参数：无。返回：文本页。异常：指定故障。"""
        self.record('textpage')
        if self.fail=='textpage':raise ValueError('synthetic textpage')
        page=_Native(self.log,self.fail);page.role='textpage';return page
    def get_text_range(self) -> str:
        """参数：无。返回：文本。异常：指定故障。"""
        self.record('read')
        if self.fail=='read':raise ValueError('synthetic read')
        return 'synthetic'
    def close(self) -> None:
        """参数：无。返回：无。异常：指定close故障。"""
        self.record('close_'+self.role)
        if self.fail=='close_'+self.role:raise ValueError('synthetic close')
    def record(self, event: str) -> None:
        """参数：事件。返回：无。异常：无。"""
        self.log.append((event,threading.get_ident()))


@pytest.mark.parametrize('fail', ('','open','textpage','read','close_textpage','close_page','close_document'))
def test_native_lifetime(tmp_path: Path,monkeypatch: pytest.MonkeyPatch,fail: str) -> None:
    """所有close显式逆序且同线程，异常不依赖GC。参数：注入阶段。返回：无。异常：遗漏断言失败。"""
    log: list[tuple[str,int]]=[]
    native=_Native(log,fail)
    monkeypatch.setattr(worker.importlib,'import_module',lambda name:native)
    path=tmp_path/'input.pdf'
    path.write_bytes(b'%PDF-test')
    result=PdfTextWorker(str(path),3)()
    assert isinstance(result,dict)
    assert len({thread for _,thread in log})==1
    calls=[name for name,_ in log]
    if fail=='open':assert calls==['open']
    else:
        assert calls[-1]=='close_document'
        if fail!='textpage':assert calls.index('close_textpage')<calls.index('close_page')<calls.index('close_document')
    if fail:assert result['error']==('close' if fail.startswith('close') else 'native')
    else:assert result['pages']==['synthetic','synthetic']


def test_real_parallel_spawn_and_running_loop() -> None:
    """两个并行调用各有不同PID；已有loop的同步接口也完成回收。

    参数：无。返回：无。异常：共享PID、空文本或孤儿进程断言失败。
    """
    payload=official_inputs()[0][1]
    before={p.pid for p in multiprocessing.active_children()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=[f.result() for f in [pool.submit(extract_hk_pages,payload),pool.submit(extract_hk_pages,payload)]]
    assert a.worker_pid!=b.worker_pid and os.getpid() not in (a.worker_pid,b.worker_pid)
    assert len(a.pages)==len(b.pages)==3 and a.pages==b.pages
    async def inside_loop() -> None:
        """参数：无。返回：无。异常：嵌套loop错误透传。"""
        result=extract_hk_pages(payload)
        assert result.pages==a.pages
    asyncio.run(inside_loop())
    assert {p.pid for p in multiprocessing.active_children()}==before


@dataclass(frozen=True)
class _SlowWorker:
    """实际spawn中模拟阻塞native，父侧必须强制回收。"""
    input_path: str
    max_pages: int
    def __call__(self) -> JsonValue:
        """参数：无。返回：不在取消前返回。异常：无。"""
        time.sleep(10)
        return None


@dataclass(frozen=True)
class _CrashedWorker:
    """实际spawn退出但无IPC消息。"""
    input_path: str
    max_pages: int
    def __call__(self) -> JsonValue:
        """参数：无。返回：无。异常：直接退出。"""
        os._exit(19)


@pytest.mark.parametrize('when',('before','waiting','native','result'))
def test_cancel_reaps_actual_process(monkeypatch: pytest.MonkeyPatch,when: str) -> None:
    """Host取消优先于确认并回收实际worker。参数：取消时机。返回：无。异常：泄漏/错误类型失败。"""
    before={p.pid for p in multiprocessing.active_children()}
    calls=0
    if when in ('waiting','native'):monkeypatch.setattr(extraction,'PdfTextWorker',_SlowWorker)
    payload=official_inputs()[0][1]
    start=time.monotonic()
    def checkpoint() -> None:
        """参数：无。返回：未取消无值。异常：指定取消。"""
        nonlocal calls
        calls+=1
        if when=='before' or when=='waiting' and calls>=3 or when=='native' and time.monotonic()-start>1:
            raise CnDownloadCancelledError('synthetic Host cancel')
        if when=='result' and calls>=5:raise CnDownloadCancelledError('result cancel')
    with pytest.raises(CnDownloadCancelledError):extract_hk_pages(payload,checkpoint)
    assert {p.pid for p in multiprocessing.active_children()}==before


def test_actual_crash_and_async_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    """崩溃与Task.cancel分别保留执行错误/取消且无子进程。参数：注入。返回：无。异常：断言失败。"""
    before={p.pid for p in multiprocessing.active_children()}
    monkeypatch.setattr(extraction,'PdfTextWorker',_CrashedWorker)
    with pytest.raises(HkBodyExtractionError) as error:extract_hk_pages(b'%PDF-x')
    assert error.value.reason=='crash' and 'process_exited_without_result' in error.value.detail
    monkeypatch.setattr(extraction,'PdfTextWorker',_SlowWorker)
    async def cancel() -> None:
        """参数：无。返回：无。异常：取消被吞断言失败。"""
        task=asyncio.create_task(extract_hk_pages_async(b'%PDF-x',None))
        await asyncio.sleep(.15)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(cancel())
    assert {p.pid for p in multiprocessing.active_children()}==before


@pytest.mark.parametrize('value',(None,{}, {'protocol':'bad'}, {'protocol':'pdf-text-v1','pages':[1]},
    {'protocol':'pdf-text-v1','error':'native','error_type':'ValueError','message':'synthetic'}))
def test_ipc_invalid(value: JsonValue) -> None:
    """损坏IPC不能当unknown。参数：合成消息。返回：无。异常：未拒绝失败。"""
    with pytest.raises(HkBodyExtractionError):_decode(value,b'%PDF-x')


class _FailureHandle:
    """注入启动/IPC/父侧cleanup故障，验证caller始终关闭且不转unknown。"""
    failure = ''
    closed = False
    def __init__(self,target: extraction.PdfTextWorker) -> None:
        """参数：target。返回：无。异常：无。"""
        type(self).closed=False
    def start(self) -> None:
        """参数：无。返回：无。异常：可注入启动失败。"""
        if self.failure=='startup':raise OSError('synthetic startup')
    async def wait(self,timeout_seconds: float) -> InterruptibleProcessCompleted:
        """参数：轮询预算。返回：损坏IPC。异常：可注入等待错误。"""
        if self.failure=='result':raise OSError('synthetic IPC')
        return InterruptibleProcessCompleted(None,0)
    async def close(self,*,kill_grace_seconds: float) -> None:
        """参数：回收预算。返回：无。异常：可注入cleanup错误。"""
        type(self).closed=True
        if self.failure=='cleanup':raise OSError('synthetic cleanup')


@pytest.mark.parametrize('failure',('startup','result','ipc','cleanup'))
def test_execution_failures_not_unknown(monkeypatch: pytest.MonkeyPatch,failure: str) -> None:
    """执行错误保留typed阶段且所有路径close。参数：故障。返回：无。异常：吞错失败。"""
    _FailureHandle.failure=failure
    monkeypatch.setattr(extraction,'InterruptibleProcessHandle',_FailureHandle)
    with pytest.raises(HkBodyExtractionError) as error:extract_hk_pages(b'%PDF-x')
    if failure == 'cleanup':
        assert error.value.reason == 'ipc'
        assert isinstance(error.value.__cause__, HkBodyExtractionError)
        assert error.value.__cause__.reason == 'cleanup'
    else:
        assert error.value.reason == failure
    assert _FailureHandle.closed


def test_native_invalid_pdf_is_execution_error() -> None:
    """可见native错误不是正常正文不足。参数：无。返回：无。异常：类型错误失败。"""
    with pytest.raises(HkBodyExtractionError) as error:extract_hk_pages(b'%PDF-invalid')
    assert error.value.reason=='native'


class _BlockingDiscovery:
    """用真实提取调用验证发现线程的Task取消，不产生候选。"""
    completed = False
    def resolve_company(self, query: 'CnReportQuery') -> 'CnCompanyProfile':
        """本测试不用公司解析。参数：查询。返回：无。异常：无。"""
        return CnCompanyProfile('hkexnews','HKEX:229','fixture','0135')
    def list_report_candidates(self, query: 'CnReportQuery', profile: 'CnCompanyProfile', *,
        local_annual_ends: tuple['HkAnnualAnchor',...], local_report_pdfs: tuple['CnReportPdf',...],
        pdf_download_gate: 'CnDownloadPdfGateProtocol', local_body_evidence: tuple['HkBodyEvidence',...] = (),
        cancellation_checkpoint: 'Callable[[],None] | None' = None) -> 'CnReportDiscoveryResult':
        """参数：完整发现输入。返回：空结果。异常：取消应在真实worker等待中传播。"""
        extract_hk_pages(b'%PDF-test',cancellation_checkpoint)
        self.completed=True
        return CnReportDiscoveryResult((),(),(),())
    def download_report_pdf(self, candidate: 'CnReportCandidate') -> 'DownloadedReportAsset':
        """参数：候选。返回：无。异常：不允许在测试中下载。"""
        raise AssertionError('no publication')


from collections.abc import Callable
from datetime import date
from dayu.fins.pipelines.cn_download_models import CnReportQuery,CnCompanyProfile,CnReportPdf,CnReportDiscoveryResult,CnReportCandidate,DownloadedReportAsset,HkAnnualAnchor,HkBodyEvidence
from dayu.fins.pipelines.cn_download_pdf_gate import CnDownloadPdfGateProtocol,NoopCnDownloadPdfGate
from dayu.fins.pipelines.cn_download_workflow import _discover_reports
from tests.fins.test_hk_body_period import QUERY


def test_discovery_task_cancel_waits_for_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    """发现Task取消后线程/worker一起收口，不能后台确认。

    参数：注入阻塞native。返回：无。异常：取消被吞、确认或子进程残留断言失败。
    """
    monkeypatch.setattr(extraction,'PdfTextWorker',_SlowWorker)
    before={p.pid for p in multiprocessing.active_children()}
    client=_BlockingDiscovery()
    async def run() -> None:
        """参数：无。返回：无。异常：取消保留。"""
        task=asyncio.create_task(_discover_reports(client,QUERY,
            CnCompanyProfile('hkexnews','HKEX:229','fixture','0135'),local_annual_ends=(),local_report_pdfs=(),
            local_body_evidence=(),
            pdf_download_gate=NoopCnDownloadPdfGate(),cancellation_checkpoint=None))
        await asyncio.sleep(.15)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(run())
    assert not client.completed and {p.pid for p in multiprocessing.active_children()}==before


def test_repeated_cancel_waits_for_real_worker_and_discovery_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    """重复 Task 取消仍等待真实进程及拥有它的发现线程。

    参数：monkeypatch 注入有界阻塞 worker。返回：无。异常：提前返回或遗留进程断言失败。
    """
    monkeypatch.setattr(extraction, 'PdfTextWorker', _SlowWorker)
    before = {p.pid for p in multiprocessing.active_children()}
    client = _BlockingDiscovery()

    async def run() -> None:
        """驱动两层重复取消。参数：无。返回：无。异常：取消未传播断言失败。"""
        task = asyncio.create_task(_discover_reports(client, QUERY,
            CnCompanyProfile('hkexnews', 'HKEX:229', 'fixture', '0135'),
            local_annual_ends=(), local_report_pdfs=(), local_body_evidence=(),
            pdf_download_gate=NoopCnDownloadPdfGate(), cancellation_checkpoint=None))
        await asyncio.sleep(.15)
        task.cancel()
        await asyncio.sleep(.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert not client.completed
    assert {p.pid for p in multiprocessing.active_children()} == before


from dayu.fins.pipelines.cn_download_protocols import CnReportDiscoveryClientProtocol


class _SuccessfulHandle(_FailureHandle):
    """准确返回成功IPC，控制关闭竞态。"""
    payload=b'%PDF-x'
    closing_started: asyncio.Event | None = None
    async def wait(self,timeout_seconds: float) -> InterruptibleProcessCompleted:
        """参数：预算。返回：合法IPC。异常：无。"""
        return InterruptibleProcessCompleted({'protocol':'pdf-text-v1','sha256':hashlib.sha256(self.payload).hexdigest(),
            'pages':['synthetic'],'pid':123,'thread':456},0)
    async def close(self,*,kill_grace_seconds: float) -> None:
        """参数：回收预算。返回：无。异常：无。"""
        if self.closing_started is not None:
            self.closing_started.set()
            await asyncio.sleep(.1)
        type(self).closed=True


def test_cancellation_after_result_and_during_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """接收后/关闭期间取消均不成功返回，且关闭完成。

    参数：注入合法IPC和关闭交错。返回：无。异常：确认竞态或未等待关闭断言失败。
    """
    monkeypatch.setattr(extraction,'InterruptibleProcessHandle',_SuccessfulHandle)
    _SuccessfulHandle.closing_started=None
    _SuccessfulHandle.closed=False
    def checkpoint() -> None:
        """参数：无。返回：无。异常：回收后Host取消。"""
        if _SuccessfulHandle.closed:raise CnDownloadCancelledError('cancel after cleanup')
    with pytest.raises(CnDownloadCancelledError):extract_hk_pages(_SuccessfulHandle.payload,checkpoint)
    async def run() -> None:
        """参数：无。返回：无。异常：取消原样。"""
        _SuccessfulHandle.closing_started=asyncio.Event()
        task=asyncio.create_task(extract_hk_pages_async(_SuccessfulHandle.payload,None))
        await _SuccessfulHandle.closing_started.wait()
        task.cancel()
        await asyncio.sleep(.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert _SuccessfulHandle.closed
    asyncio.run(run())


def test_main_import_failure_with_large_input_is_bounded() -> None:
    """真实spawn在target反序列化前失败时，大原件也必须typed收口并回收。

    参数：无。返回：无。异常：阻塞超过预算、丢失错误或资源泄漏时失败。
    """
    import subprocess
    import sys
    result=subprocess.run([sys.executable,str(Path(__file__).parent/'fixtures/hk_broken_spawn_entry.py')],
        capture_output=True,text=True,timeout=20,check=False)
    assert result.returncode==0 and '"reason": "crash"' in result.stdout
    assert 'synthetic main import failure' in result.stderr


from tempfile import TemporaryDirectory


class _DirectoryConstructionFailure(TemporaryDirectory[str]):
    """注入同次输入目录创建失败。"""
    def __init__(self,*,prefix: str) -> None:
        """参数：前缀。返回：无。异常：模拟创建失败。"""
        raise OSError('synthetic input construction')


class _DirectoryCleanupFailure(TemporaryDirectory[str]):
    """删除实际输入后报告清理失败，验证typed错误保留。"""
    def cleanup(self) -> None:
        """参数：无。返回：无。异常：模拟回收失败。"""
        super().cleanup()
        raise OSError('synthetic input cleanup')


def test_cancel_and_input_cleanup_failure_keep_both_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    """真实 worker 取消与输入清理失败并发时仍传播取消且附带清理原因。

    参数：monkeypatch 注入有界阻塞及清理故障。返回：无。异常：取消或诊断丢失断言失败。
    """
    monkeypatch.setattr(extraction, 'PdfTextWorker', _SlowWorker)
    monkeypatch.setattr(extraction, 'TemporaryDirectory', _DirectoryCleanupFailure)
    before = {p.pid for p in multiprocessing.active_children()}

    async def run() -> None:
        """驱动真实子进程取消。参数：无。返回：无。异常：诊断不一致断言失败。"""
        task = asyncio.create_task(extract_hk_pages_async(b'%PDF-test', None))
        await asyncio.sleep(.15)
        task.cancel()
        task.cancel()
        with pytest.raises(asyncio.CancelledError) as error:
            await task
        assert isinstance(error.value.__cause__, HkBodyExtractionError)
        assert error.value.__cause__.reason == 'cleanup'

    asyncio.run(run())
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_input_descriptor_failures_are_typed(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    """同次输入创建/读取/清理失败不能伪装unknown。

    参数：隔离临时目录和故障注入。返回：无。异常：吞错或阶段丢失断言失败。
    """
    value=PdfTextWorker(str(tmp_path/'missing.pdf'),3)()
    assert isinstance(value,dict) and value['error']=='input'
    monkeypatch.setattr(extraction,'TemporaryDirectory',_DirectoryConstructionFailure)
    with pytest.raises(HkBodyExtractionError) as error:extract_hk_pages(b'%PDF-x')
    assert error.value.reason=='startup'
    monkeypatch.setattr(extraction,'TemporaryDirectory',_DirectoryCleanupFailure)
    monkeypatch.setattr(extraction,'InterruptibleProcessHandle',_SuccessfulHandle)
    _SuccessfulHandle.closing_started=None
    with pytest.raises(HkBodyExtractionError) as error:extract_hk_pages(_SuccessfulHandle.payload)
    assert error.value.reason=='cleanup'
