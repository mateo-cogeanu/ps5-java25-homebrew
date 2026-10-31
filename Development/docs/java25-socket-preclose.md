# PS5 socket pre-close — patch0135

Consumer173 reaches the world, but returning to the title screen causes SVC's
DatagramSocket.close to throw java.lang.Error wrapping an IOException from
UnixDispatcher.preClose0: the title sandbox rejects dup2 with EPERM. This is a
runtime socket-lifecycle failure; the controller merely invokes the menu action.
The retained run has no JVM abort record. Raw reports remain local.

On PS5 only, preClose0 now shuts down socket I/O in both directions, retrying
EINTR and accepting ENOTCONN for unconnected UDP/listening sockets. It does not
close the descriptor. The existing Java closing state, NativeThread signals,
reader/writer ownership and end/tryClose final close remain responsible for
releasing it. Thus late I/O cannot touch a recycled descriptor. Other shutdown
errors propagate; ENOTSOCK retains the existing non-socket dup2/error path.
Other platforms retain their original dup2 behavior. This is not a general
file-descriptor-duplication implementation or an arbitrary sandbox bypass.

The actual JNI method is registered in a host JDK25. Forty repetitions each of
blocked UDP receive, TCP read and listening accept close pass with bounded joins;
EINTR/ENOTCONN, genuine EPERM/EBADF, unchanged non-socket/desktop errors and
subsequent socket use are checked under XcheckJNI/UBSan. These host kernels do
not prove PS5 shutdown/wakeup semantics. The genuine PS5 java.base libraries
rebuild; hashes and results are in [validation](java25-socket-preclose-validation.json).

Run `python3 tools/test_java25_socket_preclose.py --java-home /path/to/jdk25`.
Consumer174 must integrate the rebuilt UnixDispatcher object and validate
return-to-title, blocked voice receive shutdown, repeat world/server joins and
save integrity on the console. No exact-build console pass or release is claimed.
