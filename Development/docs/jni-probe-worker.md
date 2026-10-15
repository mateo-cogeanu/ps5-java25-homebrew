# JNI probe worker

`java25/probe/jni_worker.hpp` provides a main-thread-owned job for long JNI probe calls. It creates a pthread with an explicit 8 MiB stack, attaches that thread to the existing VM, invokes its callback with the thread-owned `JNIEnv`, then detaches. The main thread polls completion and joins before consuming results or destroying the VM. Never share the creating thread’s `JNIEnv` with the callback.

The consumer must hide callback-written buffers while the worker runs. The release/acquire completion flag and join publish those writes; they do not synchronize reads made before completion. The callback must handle Java exceptions and must not throw a C++ exception. Keep the job and callback context alive through join.

An attached thread begins with a bootstrap context class loader. A fixture that uses system-class-path service discovery must explicitly set its thread context loader before starting Java child threads. Worker execution keeps the UI event loop available, but native fatal signals still terminate the entire process. It does not provide cancellation, a startup timeout or crash recovery.

Run `python3 tools/test_jni_worker.py` against the host JDK. This builds a real-JVM fixture runner under `build/java25/jni-worker-test/`; consumers can use it to run their actual Java entry point on an attached worker. The test checks attachment, separate JNI environments, context-loader inheritance, main-loop progress, detach/join, invalid starts and VM destruction. Target linking and host success do not establish a PS5 pass.
