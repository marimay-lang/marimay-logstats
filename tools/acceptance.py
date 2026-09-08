#!/usr/bin/env python3
"""Application-owned synthetic cases over the unmodified acceptance driver v1."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from mmay_acceptance import Application
ROOT = Path(__file__).resolve().parents[1]
APP = Application(ROOT, timeout=180)
WORK = ROOT / "build" / "acceptance"
WORK.mkdir(parents=True, exist_ok=True)
DATA = WORK / "input ü.txt"
started = time.monotonic()
engines = APP.engines(WORK, "app", ["--allow-read", str(WORK), "--max-heap-bytes", "33554432"])
results = []

def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"

def case(arguments, data, expected, selected=None):
    def verify(engine, result):
        assert (result.stdout, result.stderr) == expected[1:], (arguments, engine, result.stdout, result.stderr, expected)
    APP.compare(engines if selected is None else selected, arguments, expected[0], data=data, verify=verify)
    results.append({"arguments": arguments, "data_sha256": hashlib.sha256(data or b"").hexdigest(),
                    "status": expected[0], "stdout_sha256": hashlib.sha256(expected[1]).hexdigest(),
                    "stderr": expected[2].decode()})

def err(message):
    return (ROOT.name + ": " + message + "\n").encode()

def report(lines, levels, events):
    return encoded({"lines":lines,"levels":dict(zip(["debug","info","warn","error"],levels)),
                    "events":[{"event":event,"count":count} for event,count in events]})
sample = "INFO\tстарт\r\nERROR\tстарт\nWARN\t🌿".encode()
case(["-"], sample, (0,report(3,[0,1,1,1],[("старт",2),("🌿",1)]),b""))
case(["-"], b"", (0,report(0,[0,0,0,0],[]),b""))
for bad in [b"",b"INFO",b"INFO\t",b"INFO\tx\textra"]:
    case(["-"], b"INFO\tx\n"+bad+b"\n", (1,b"",err("-: строка 2: Ожидается УРОВЕНЬ<TAB>СОБЫТИЕ")))
case(["-"], b"info\tx", (1,b"",err("-: строка 1: Неизвестный уровень")))
case(["-"], b"DEBUG\ta\0b", (0,report(1,[1,0,0,0],[("a\0b",1)]),b""))
case(["-", "--max-keys", "1"], b"INFO\tx\nWARN\tx", (0,report(2,[0,1,1,0],[("x",2)]),b""))
case(["-", "--max-keys", "1"], b"INFO\tx\nWARN\ty", (1,b"",err("-: Превышен лимит 1 событий")))
large = (b"INFO\t"+b"x"*122+b"\n")*16384
expected_large = report(16384,[0,16384,0,0],[("x"*122,16384)])
case(["-"], large, (0,expected_large,b""))
DATA.write_bytes(large)
case([str(DATA)], None, (0,expected_large,b""))
DATA.write_bytes(sample)
case([str(DATA), str(DATA)], None, (0,report(6,[0,2,2,2],[("старт",4),("🌿",2)]),b""))
DATA.write_bytes(large)
boundary = "x"*4090+"🌿"
case(["-","--max-line","4099"],b"INFO\t"+boundary.encode()+b"\r\n",(0,report(1,[0,1,0,0],[(boundary,1)]),b""))
keys = [f"событие-{i:04d}" for i in range(4096)]
key_input = ("\n".join("INFO\t"+value for value in keys)+"\n").encode()
case(["-","--max-keys","4096"],key_input,(0,report(4096,[0,4096,0,0],[(value,1) for value in keys]),b""))
error_status = 1
base_args = []
broken_args, broken_data = ["-"], b"INFO\tx\n"
case([*base_args, "-", "--max-line", "1"], b"ab\n", (error_status,b"",err("-: standard input line exceeds 1-byte limit")))
case([*base_args, "-"], b"a\xff\n", (error_status,b"",err("-: standard input is not valid UTF-8")))
missing = WORK / "missing"
case([*base_args, str(missing)], None, (error_status,b"",err(str(missing)+": filesystem path was not found")))
usage = {
  "--unknown": f"unknown option --unknown at argument {len(base_args)+1}",
  "--max-line=-1": "--max-line: допустимо 0..1048576",
  "--max-line=1048577": "--max-line: допустимо 0..1048576",
  "--max-line=no": "--max-line: ожидается целое число",
}
for flag,message in usage.items():
    case([*base_args,"-",flag],b"",(2,b"",err(message)))
case([],b"",(2,b"",err("Нужен ФАЙЛ; см. --help")))
def verify_help(engine,result):
    assert not result.stderr and ROOT.name.encode() in result.stdout, (engine,result)
help_result = APP.compare(engines,["--help"],0,verify=verify_help)
results.append({"arguments":["--help"],"status":0,"stdout_sha256":hashlib.sha256(help_result[1]).hexdigest(),"stderr":""})

denied_bin = WORK / "denied"
APP.successful([APP.compiler,"build",".","--release","--output",str(denied_bin)])
denied = {"vm":[APP.compiler,"run",".","--"],"release":[str(denied_bin)]}
case([*base_args,str(DATA)], None, (error_status,b"",err(str(DATA)+": fs.read capability denied for "+str(DATA))), selected=denied)
pipes = []
if os.name != "nt":
    link = WORK / "link"
    if link.is_symlink(): link.unlink()
    link.symlink_to(DATA)
    case([*base_args,str(link)],None,(error_status,b"",err(str(link)+": symbolic links are not followed")))
    for engine,prefix in engines.items():
        read_fd,write_fd = os.pipe(); os.close(read_fd)
        try: child = subprocess.Popen([*prefix,*broken_args],cwd=ROOT,stdin=subprocess.PIPE,stdout=write_fd,stderr=subprocess.PIPE)
        finally: os.close(write_fd)
        _,error = child.communicate(broken_data,timeout=180)
        assert child.returncode == error_status and (b"standard stream write failed" in error or b"standard stream flush failed" in error), (engine,child.returncode,error)
        pipes.append({"engine":engine,"status":child.returncode,"stderr":error.decode()})
assert DATA.read_bytes() == large
report_data = {"schema":ROOT.name+".acceptance/1","harness":APP.metadata(engines),"cases":results,"closed_pipes":pipes,
               "large_bytes":len(large),"managed_heap_limit":33554432,"elapsed_seconds":time.monotonic()-started}
(WORK / "report.json").write_text(json.dumps(report_data,ensure_ascii=False,indent=2)+"\n")
print(f"{ROOT.name}: {len(results)} cases; VM/native Debug/Release; {len(pipes)} pipes; {len(large)}-byte input")
