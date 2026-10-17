# Reuse compatible native slab capacity under pressure

Patch0068 follows a console failure in which a16-byte raw allocation could not
obtain either a64KiB or minimal16KiB mapping. This establishes genuine mapping
refusal, not the overall process limit or the availability of other slab slots.

The raw allocator previously inspected only its own size class. After both
mapping attempts fail, it now searches successively larger classes for an
available slot. The existing ownership header retains the actual slab; free
and realloc preserve its index, mapping size and lifetime. Smaller slots are
never eligible. The allocator lock covers selection and ownership transfer.
If no compatible slot exists, the original allocation failure is retained.

On complete small-allocation failure, the trace snapshots each class's mapped
bytes, live slots and free slots while holding the lock, then emits the results
after unlocking. This measures only these fallback slabs, not all native memory
or the process budget. Successful borrowing reports requested and actual slot
capacity. No extra reserve, heap-size change or allocation-success fabrication
is introduced.

Validation: actual-header ASan/UBSan regressions force all mappings to fail,
fill larger slabs with16-byte borrowed blocks, exhaust them, check owner-first
release and final unmapping, reject undersized slots, and preserve bytes after
failed realloc. Existing concurrent lifetime and os.cpp API/NMT-contract-model
tests pass. Target HotSpot/java.base-libs rebuild passes; target library contains
the new diagnostics. Console usefulness and overall exhaustion remain unproven.
