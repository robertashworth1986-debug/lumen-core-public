from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
source = root / "address_positive_control.c"
source.write_text('#include <stdlib.h>\nint main(int argc, char **argv) {\nvolatile char *p=malloc(1); (void)argv; if(!p)return 2; p[argc+3]=120; free((void*)p); return 0;}\n')
rows = []
for name, flags in [('combined', ['-fsanitize=address,undefined']), ('separate', ['-fsanitize=address', '-fsanitize=undefined']), ('address', ['-fsanitize=address'])]:
    executable = root / f"address_control_{name}.exe"
    command = [sys.executable, '-m', 'ziglang', 'cc', '-std=c11', '-O0', '-g', *flags,
               '-fno-sanitize-recover=all', str(source), '-o', str(executable)]
    compiled = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=120)
    (root / f"address_control_{name}_compile.log").write_text(compiled.stdout + compiled.stderr)
    row = {'mode': name, 'flags': flags, 'compile_exit': compiled.returncode}
    if compiled.returncode == 0:
        ran = subprocess.run([str(executable)], cwd=root, capture_output=True, text=True, timeout=20)
        (root / f"address_control_{name}_run.log").write_text(ran.stdout + ran.stderr)
        row.update({'run_exit': ran.returncode, 'asan_diagnostic': 'AddressSanitizer' in ran.stderr,
                    'diagnostic_preview': ran.stderr[:200]})
    rows.append(row)
    print(json.dumps(row), flush=True)
(root / 'address-control-modes.json').write_text(json.dumps(rows, indent=2) + '\n')
