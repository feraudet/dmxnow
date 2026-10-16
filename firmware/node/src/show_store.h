// Stored show in the "spiffs" data partition (128 kB, partitions.csv), read through a
// flash mapping (PROTOCOL §10, SPEC 4.13). Upload: SHOW_WRITE chunks from offset 0,
// each 4 kB sector erased just before it is first written.
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace show_store {

bool begin();                   // finds and maps the partition
const uint8_t* data();          // mapped partition, nullptr if absent
size_t capacity();

// offset 0 starts a new upload (the previous show is lost as soon as its first sector
// is erased); afterwards each chunk must start at or before the erased end.
dmxnow::AckStatus write(uint32_t offset, const uint8_t* d, size_t n);
void remap();                   // after an upload: fresh mapping, no stale cache line
bool clear();                   // erases the first sector: no valid show any more

}  // namespace show_store
