# Java 17 pending exception trace

Consumer 021 stopped after the original Minecraft Main class initialized.
Its retained fault log did not grow, and neither Java failure reporting
nor the JNI return checkpoint ran. The precise failure is unresolved.

The active PS5 Java 17 runtime offers an explicit exception tracing
setter. After enablement, up to 128 pending exception installations
record a bounded class name and VM source line using fixed stack buffers.
The trace uses existing private file output and does not invoke Java,
allocate memory, modify the exception or change exception handling.
The default is disabled. The record budget is process-wide and is not
reset by toggling the setter.

Consumer 022 enables the trace at the original Main checkpoint and
disables it after JNI returns. Exact PS5 startup remains pending.

The PS5 022 run returned InvocationTargetException with a ClassFormatError
cause. Several ClassFormatError installations were recorded before JNI
returned, followed by clean VM destruction. Active diagnostics now include
the VM source basename and a bounded ClassFormatError detail copied into
caller-provided stack storage. Raw report text stays local. Exact rejected
class and failure origin are pending the next console run.
