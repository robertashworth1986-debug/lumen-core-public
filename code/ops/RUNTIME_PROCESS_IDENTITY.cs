// Bounded Windows process leases for STACK_RUNTIME_MANAGER.ps1.
// A held handle, creation time and image path prevent PID reuse from inheriting
// a previously recorded process's stop authority. This is not a user boundary.
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace LumenCore.RuntimeV2 {
    public sealed class ProcessLease : IDisposable {
        private IntPtr handle;
        public readonly int ProcessNumber;
        public readonly ulong CreationFileTime;
        public readonly string ImagePath;

        [StructLayout(LayoutKind.Sequential)]
        private struct FileTime { public uint Low; public uint High; }
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern IntPtr OpenProcess(uint access, bool inherit, int processNumber);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetProcessTimes(IntPtr process, out FileTime created, out FileTime exited, out FileTime kernel, out FileTime user);
        [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
        private static extern bool QueryFullProcessImageName(IntPtr process, uint flags, StringBuilder image, ref uint length);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern uint WaitForSingleObject(IntPtr value, uint timeout);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool TerminateProcess(IntPtr process, uint exitCode);
        [DllImport("kernel32.dll")]
        private static extern bool CloseHandle(IntPtr value);
        [DllImport("kernel32.dll")]
        private static extern IntPtr GetCurrentProcess();
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool DuplicateHandle(IntPtr sourceProcess, IntPtr source, IntPtr targetProcess,
            out IntPtr duplicate, uint access, bool inherit, uint options);
        [DllImport("shell32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
        private static extern IntPtr CommandLineToArgvW(string command, out int count);
        [DllImport("kernel32.dll")]
        private static extern IntPtr LocalFree(IntPtr value);

        public ProcessLease(int processNumber, bool allowStop) : this(processNumber,
            OpenProcess(0x00101000U | (allowStop ? 1U : 0U), false, processNumber)) { }

        private ProcessLease(int processNumber, IntPtr ownedHandle) {
            handle = ownedHandle;
            if (processNumber <= 0) throw new ArgumentOutOfRangeException("processNumber");
            ProcessNumber = processNumber;
            if (handle == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
            try {
                FileTime created, exited, kernel, user;
                if (!GetProcessTimes(handle, out created, out exited, out kernel, out user))
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                CreationFileTime = ((ulong)created.High << 32) | created.Low;
                uint length = 32768;
                StringBuilder image = new StringBuilder((int)length);
                if (!QueryFullProcessImageName(handle, 0, image, ref length))
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                ImagePath = Path.GetFullPath(image.ToString());
            } catch { Dispose(); throw; }
        }

        public static ProcessLease FromStartedProcess(System.Diagnostics.Process process) {
            // Process.Start retains the returned native handle. Duplicate that
            // handle rather than reopening a numeric PID after the launch.
            IntPtr duplicate;
            IntPtr current = GetCurrentProcess();
            if (!DuplicateHandle(current, process.Handle, current, out duplicate, 0, false, 2))
                throw new Win32Exception(Marshal.GetLastWin32Error());
            return new ProcessLease(process.Id, duplicate);
        }

        public bool Alive {
            get {
                if (handle == IntPtr.Zero) throw new ObjectDisposedException("ProcessLease");
                uint state = WaitForSingleObject(handle, 0);
                if (state == 0) return false;
                if (state == 258) return true;
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
        }

        public bool Matches(ulong created, string image) {
            return CreationFileTime == created &&
                String.Equals(ImagePath, Path.GetFullPath(image), StringComparison.OrdinalIgnoreCase);
        }

        public void StopVerified(ulong created, string image) {
            if (!Matches(created, image)) throw new InvalidOperationException("process identity changed; stop blocked");
            if (!Alive) return;
            if (!TerminateProcess(handle, 1)) throw new Win32Exception(Marshal.GetLastWin32Error());
            if (WaitForSingleObject(handle, 5000) != 0) throw new TimeoutException("registered process exit was not confirmed");
        }

        public void Dispose() {
            if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; }
            GC.SuppressFinalize(this);
        }
        ~ProcessLease() { Dispose(); }

        public static string[] ParseCommand(string command) {
            if (String.IsNullOrWhiteSpace(command) || command.Length > 32768)
                throw new ArgumentException("missing or oversized process command");
            int count;
            IntPtr argv = CommandLineToArgvW(command, out count);
            if (argv == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
            try {
                if (count < 1 || count > 4096) throw new ArgumentException("invalid argument count");
                string[] result = new string[count];
                for (int index=0; index<count; index++)
                    result[index] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(argv, index * IntPtr.Size));
                return result;
            } finally { LocalFree(argv); }
        }

        public static string QuoteArgument(string argument) {
            if (argument == null || argument.IndexOf('\0') >= 0) throw new ArgumentException("invalid argument");
            StringBuilder result = new StringBuilder("\"");
            int slashes = 0;
            foreach (char value in argument) {
                if (value == '\\') { slashes++; continue; }
                if (value == '"') { result.Append('\\', slashes * 2 + 1); result.Append(value); }
                else { result.Append('\\', slashes); result.Append(value); }
                slashes = 0;
            }
            result.Append('\\', slashes * 2); result.Append('"');
            return result.ToString();
        }
    }
}
