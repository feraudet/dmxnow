#include "show_store.h"

#include <esp_partition.h>
#include <spi_flash_mmap.h>

#include "dmxnow/show.h"

namespace show_store {

namespace {
constexpr size_t kSector = 4096;
const esp_partition_t* part = nullptr;
const void* mapped = nullptr;
esp_partition_mmap_handle_t handle;
uint32_t erased_end = 0;   // [0, erased_end) erased by the current upload

void map() {
    if (!part || mapped) return;
    if (esp_partition_mmap(part, 0, part->size, ESP_PARTITION_MMAP_DATA, &mapped, &handle) != ESP_OK)
        mapped = nullptr;
}

void unmap() {
    if (!mapped) return;
    esp_partition_munmap(handle);
    mapped = nullptr;
}
}  // namespace

bool begin() {
    part = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "spiffs");
    map();
    return mapped != nullptr;
}

const uint8_t* data() { return static_cast<const uint8_t*>(mapped); }
size_t capacity() { return part ? part->size : 0; }

dmxnow::AckStatus write(uint32_t offset, const uint8_t* d, size_t n) {
    if (!part) return dmxnow::AckStatus::Unsupported;
    if (n == 0 || offset + n > part->size) return dmxnow::AckStatus::InvalidArg;
    if (offset == 0) {
        unmap();   // the player is stopped by the caller, nothing reads the mapping now
        erased_end = 0;
    }
    if (offset > erased_end) return dmxnow::AckStatus::InvalidArg;   // a chunk is missing
    while (erased_end < offset + n) {
        if (esp_partition_erase_range(part, erased_end, kSector) != ESP_OK) return dmxnow::AckStatus::InternalError;
        erased_end += kSector;
    }
    // a repeated chunk (CLI retry) writes the same bits again: harmless on NOR flash
    if (esp_partition_write(part, offset, d, n) != ESP_OK) return dmxnow::AckStatus::InternalError;
    return dmxnow::AckStatus::Ok;
}

void remap() {
    unmap();
    map();
}

bool verify(uint32_t size, uint32_t crc) {
    if (!part || size == 0 || size > part->size) return false;
    uint8_t buf[256];
    uint32_t c = 0;
    for (uint32_t off = 0; off < size; off += sizeof buf) {
        size_t n = size - off < sizeof buf ? size - off : sizeof buf;
        if (esp_partition_read(part, off, buf, n) != ESP_OK) return false;
        c = dmxnow::crc32(buf, n, c);
    }
    return c == crc;
}

bool clear() {
    if (!part) return false;
    unmap();
    erased_end = 0;
    bool ok = esp_partition_erase_range(part, 0, kSector) == ESP_OK;
    map();
    return ok;
}

}  // namespace show_store
