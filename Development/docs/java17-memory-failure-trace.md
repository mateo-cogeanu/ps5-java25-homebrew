# Java 17 memory failure trace

The Java 17 runtime for PPSA99878/01.000.017 reached Minecraft 1.20's
original Main and shut down cleanly. Main reported an unclassified
OutOfMemoryError with roughly 53 MiB of Java heap in use. This leaves
the failing allocation unresolved, including whether the heap could grow.

The active Java 17 target records the first HotSpot-reported OOM category,
up to eight failed reservation commits with size and errno, and up to
eight libjava OutOfMemoryError requests without logging their messages.
These use the existing private runtime trace path and preserve errno.
Allocation, exception and commit policies are unchanged. These events
cover the instrumented paths only.

Consumer 018 retains the 017 memory limits and adds fixed Java-side OOM
categories. Physical startup and title-screen validation remain pending.
