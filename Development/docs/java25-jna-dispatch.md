# Optional JNA native dispatch integration

`tools/java25_jna.py` compiles genuine pinned JNA5.19.1 dispatch/callback C sources for a caller's resident library group. It leaves the default core runtime unchanged. Source commit: `1a91122853f6ab6f1fb2a4a284a6cf2ed8af0a4d` from java-native-access/jna. The native ABI version7.0.4 and checksum are taken from upstream common.xml, which is authoritative; native/Makefile contains stale generated defaults and must not supply the version.

The builder generates JNI headers with the pinned upstream Java source after the same Version.java substitution used by the upstream build. Those generated Java classes are used only to produce headers. Consumers keep the original publisher JNA Java JAR intact. The native compilation retains direct buffers, memory, calls and callback implementations. JAWT and JNA's optional signal-interception protection are not enabled; no AWT or protected-invalid-pointer support is claimed.

Example target build:

```sh
python3 tools/java25_jna.py --ffi-include /path/to/compatible/libffi/include --offline
```

The target result is build/java25/jna-target/jnidispatch.o, with an audit of the pinned source hashes, generated headers and69JNI exports. It intentionally leaves libffi references unresolved. An integrating application supplies its already-compatible libffi implementation and registers the object under resident group jnidispatch. The ordinary runtime registry and loader handle ownership/lifetime; this does not add an arbitrary ELF loader. No source or alias in the default core configuration changes.

An application using JNA must let its own JNA class loader call System.loadLibrary("jnidispatch"). JNA's supported jna.nosys=false option enables that path. jna.noclasspath=true and jna.nounpack=true prevent attempting to unpack a desktop native binary. The application owns the decision to set those properties for a matching dependency. Do not preload from a different parent class loader, replace com.sun.jna.Native or bypass a native initialization failure.

Host verification:

```sh
python3 tools/test_java25_jna.py --jna-jar /path/to/original/jna-5.19.1.jar
```

The test pins the original Java artifact and forces the freshly built host dispatch through its boot path, with classpath native fallback disabled. It checks actual native sizes, last-error state, allocated memory/string round trips and real libffi strlen/abs calls. A host pass does not establish PS5 calls, callbacks, thread attachment or dynamic library compatibility. Actual target initialization and memory behavior remain pending console validation. Do not advertise universal JNA compatibility or use the absence of a native-load crash as proof that every API works.

Upstream JNA is dual Apache2.0/LGPL2.1-or-later. Retain its LICENSE/AL2.0/LGPL2.1 and source pins. Current consumer integration and game-specific validation live in [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft); reusable runtime build tooling remains here. Frozen milestones and compiled passing snapshots are untouched.
