# Checked PS5 random-service resolution

Patch0096 fixes the concrete failure captured in consumer072. Its saved SIGSEGV
has PC0. The stack's top return address, adjusted using the matching handler
anchor, is exactly after the direct sceRandomGetRandomNumber indirect call in
Java_sun_security_provider_NativeSeedGenerator_getPS5SeedBytes. The matching
ELF's GLOB_DAT relocation identifies that import. This establishes an unresolved
service import being called, rather than a Java heap or GC failure. The earlier
071failure remains unproven;072introduced this direct service dependency.

The runtime now loads only the fixed system module path through libkernel and
resolves the specific random-service NID. It checks the loader APIs, module
result, entry result, lookup result and returned pointer before calling. Missing
APIs/load/symbol/OS request failures become ProviderException. There is no
substitute seed or unchecked null call. Resolution is published once with
acquire/release ordering; other callers share the result. The module stays
resident for the cached pointer's lifetime. The direct libSceRandom link-time
dependency is removed from standalone libjava and the embedded package.

API/source provenance: [SDK v0.42 SPRX loader](https://github.com/ps5-payload-dev/sdk/blob/v0.42/crt/rtld_sprx.c),
[SDK NID implementation](https://github.com/ps5-payload-dev/sdk/blob/v0.42/crt/nid.c).
The lookup NID PI7jIZj4pcE corresponds to sceRandomGetRandomNumber. This loads a
fixed system service, not arbitrary native modules or consumer game code.

The actual Java/JNI host regression covers concurrent cold initialization,
64-byte batching and DRBG, first/later OS errors, module-load failure, symbol
lookup failure and success-with-null rejection, plus the desktop URL control.
It runs with JNI checking and UBSan using mocked module APIs and host entropy.
Target native rebuild passes. These do not establish PS5 loader availability,
OS entropy quality, successful TLS or the original071crash resolution. Those
remain console checks. No server-JAR transformations are added by this repair.
