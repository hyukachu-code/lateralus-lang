"""Independent Linux native port check, used by a read-only CI job."""
import csv
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from time import perf_counter

CASES = [(1,1), (1,400), (1899,1901), (1999,2001), (2026,2026),
         (9998,9999), (1601,2000), (1703,2599)]


def run(cmd):
    return subprocess.check_output(cmd,timeout=80).decode(errors="replace").split()


def oracle(lo,hi):
    return [str(sum(date(y,m,13).weekday()==4 for y in range(lo,hi+1))) for m in range(1,13)]


def build(source, exe):
    c=exe.with_suffix(".c")
    run([sys.executable,"-m","lateralus_lang","c",str(source),"-o",str(c)])
    run(["cc","-std=c99","-O2",str(c),"-lm","-o",str(exe)])


if __name__=="__main__":
    root=Path.cwd()
    work=root/"benchmarks/calendar_fridays"
    ltl=work/"calendar.ltl"
    py=work/"calendar_reference.py"
    with tempfile.TemporaryDirectory() as path:
        tmp=Path(path)
        exe=tmp/"calendar"
        build(ltl,exe)
        probe=tmp/"probe.ltl"
        body="\n".join(f"    print_calendar({lo}, {hi})" for lo,hi in CASES)
        probe.write_text(ltl.read_text().split("fn main()",1)[0]+"fn main() -> int {\n"+body+"\n    return 0\n}\nmain()\n")
        build(probe,tmp/"probe")
        correct=run([tmp/"probe"])==sum([oracle(a,b) for a,b in CASES],[])
        assert correct and all(run([sys.executable,py,str(a),str(b)])==oracle(a,b) for a,b in CASES)
        commands=([sys.executable,py],[exe])
        expect=oracle(1,9999)
        for cmd in commands:
            assert run(cmd)==expect
        times=[[],[]]
        for i in range(11):
            for j in (i%2,1-i%2):
                start=perf_counter()
                assert run(commands[j])==expect
                times[j].append(perf_counter()-start)
        py_time,native_time=map(statistics.median,times)
        assert native_time<py_time
        files=[p for p in work.iterdir() if p.is_file()]
        files.append(root/"BOUNTIES-LOG.md")
        print("PORT_EVIDENCE "+json.dumps(dict(python_seconds=py_time,native_seconds=native_time,
              samples=11,cases=len(CASES),full=True,head=run(["git","rev-parse","HEAD"])[0],
              hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              validator=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
