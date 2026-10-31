# Optional LLVM exception globals through compiler TLS

`tools/java25_cxxabi_tls.py` builds the genuine LLVM18.1.8
`cxa_exception_storage.cpp` HAS_THREAD_LOCAL branch, with SHA-256 pinned source
and matching header. Callers supply SDK, compiler, nm and output explicitly.
It leaves SDK archives and default runtime links unchanged. Source licensing is
Apache-2.0 WITH LLVM-exception, as indicated in the original source.

Consumer170's retained crash and matching ELF identify `__cxa_get_globals` →
`abort_message` on VoicechatSoundManag after a genuine AudioOut open refusal.
Its stderr reports `std::__libcpp_tls_set failure in __cxa_get_globals()`.
Consumer171 explicitly links this alternative object before libc++abi archives.
Both ABI entrypoints use upstream zero-initialized compiler TLS and the existing
runtime compiler-rt adapter, including its allocation policy, native identity
tracking and thread retirement. No arbitrary loader, game transformation, global
allocator change or invented exception implementation is introduced.

Target symbol audit verifies both entrypoints and `__emutls_get_address`, with no
pthread key calls. Host storage tests run 800 worker lifecycles with concurrent
isolation, clean reuse and nested throw/rethrow while pthread_setspecific returns
ENOMEM. The old LLVM threading include is unused in this branch; the host test
supplies an empty compatibility include for that obsolete filename only.
Existing actual compiler-TLS adapter failure/destructor/join tests also pass.
Host behavior does not establish target ABI, PS5 exception unwinding or cleanup.

Physical171 world launch, voice-chat playback/capture, unavailable-device error
recovery, world save/reload and endurance remain pending. The AudioOut refusal
0x8026000d is preserved as a real error; its underlying cause is unresolved.
No guarantee of a second playback device or voice-chat compatibility is made.
No frozen snapshot or release/Store approval is implied. Raw reports stay local.
