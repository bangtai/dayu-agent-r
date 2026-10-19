"""故意在spawn导入main时失败；用于验证大输入不会阻塞父进程启动管道。"""
if __name__ == '__mp_main__':
    raise RuntimeError('synthetic main import failure before target unpickle')

import json
import multiprocessing
from pathlib import Path
import tempfile
from dayu.fins.pipelines.hk_body_extraction import extract_hk_pages,HkBodyExtractionError

_LARGE_INPUT_SIZE = 1_000_000

def main() -> None:
    """参数：无。返回：无。异常：未正确失败或资源残留时断言失败。"""
    before=set(Path(tempfile.gettempdir()).glob('dayu-hk-body-*'))
    try:
        extract_hk_pages(b'%PDF-'+b'x'*_LARGE_INPUT_SIZE)
    except HkBodyExtractionError as exc:
        assert exc.reason=='crash'
        assert not multiprocessing.active_children()
        assert set(Path(tempfile.gettempdir()).glob('dayu-hk-body-*'))==before
        print(json.dumps({'reason':exc.reason,'no_remaining_children':True,'input_reclaimed':True}),flush=True)
    else:
        raise AssertionError('startup failure was not preserved')

if __name__=='__main__':
    main()
