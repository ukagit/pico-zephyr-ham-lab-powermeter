#ifndef HAMLAB_CURVES_CORE_H
#define HAMLAB_CURVES_CORE_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#define CURVES_COUNT 4
#define CURVES_POINTS 24
#define CURVES_JSON_MAX 4096
#define CURVES_MAGIC 0x43555231U
#define CURVES_SCHEMA 1U
enum curve_id { CURVE_FORWARD, CURVE_REVERSE_7, CURVE_REVERSE_50, CURVE_CURRENT };
struct curve_point { double v,w; };
struct curve_data { uint32_t frequency_hz; uint16_t count,reserved; struct curve_point points[CURVES_POINTS]; };
struct curve_bank { uint32_t magic,schema; struct curve_data curves[CURVES_COUNT]; uint32_t crc; };
extern const char *const curve_names[CURVES_COUNT];
extern const char *const curve_inputs[CURVES_COUNT];
extern const char *const curve_references[CURVES_COUNT];
extern const uint32_t curve_frequencies[CURVES_COUNT];
const char *curve_reference(enum curve_id id,uint32_t hz);
const char *curve_master(enum curve_id id,uint32_t hz);
int curves_parse(const char *json,size_t len,struct curve_bank *out,char *error,size_t error_len);
bool curves_bank_valid(const struct curve_bank *bank);
uint32_t curves_crc(const struct curve_bank *bank);
bool curves_interpolate(const struct curve_data *curve,double v,double *w);
int curves_encode(const struct curve_bank *bank,char *out,size_t len);
#endif
