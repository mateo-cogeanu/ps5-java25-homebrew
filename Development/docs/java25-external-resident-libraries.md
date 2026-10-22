# Consumer-owned resident JNI libraries

External probe specifications can now pass `resident_libraries`, a list of named groups of absolute paths to target relocatable objects:

```json
{"resident_libraries": [{"name": "consumerbridge", "objects": ["/absolute/build/consumerbridge.o"]}]}
```

The consumer builds and owns these objects. The reusable runtime packager validates ELF64 little-endian x86_64 relocatable input, names/schema/unique inputs, and rejects reserved/duplicate names and constructor sections requiring an unimplemented lifecycle. It merges each group separately, scopes JNI_OnLoad/OnUnload names, generates standard JNI_OnLoad_<name> discovery and incorporates actual exported function addresses into the existing resident library registry. A private package audit records names and object SHA-256 hashes without host paths. Inputs with no constructors are supported; general constructor/destructor and arbitrary ELF/module loading are not added.

The normal Java System.loadLibrary and JNI native-method lookup mechanisms can discover these registered resident groups. Existing dlopen/dlsym-style registry handles remain scoped to their libraries and code stays resident on close. This is a build-time embedded-library extension; it is not an operating-system dynamic linker or a promise that any third-party JNI library is compatible. There are no new HotSpot or game-class changes and no platform identity spoofing. Consumer sources remain in their own repository.

Checks cover an actual target object plus reserved/duplicate/unsafe names, nonempty/unique/absolute paths, malformed/shared ELF inputs and full-generator rejection of an actual constructor object. Target packaging compiles and links the generated registry plus a consumer JNI library. Consumer host tests exercise real System.loadLibrary/JNI_OnLoad, ordinary native method lookup, real scoped symbol/function invocation, repeated handles and absence/error controls under XcheckJNI/UBSan. The PS5 registered-library integration remains pending console validation. Existing frozen snapshots/packages are unchanged.
