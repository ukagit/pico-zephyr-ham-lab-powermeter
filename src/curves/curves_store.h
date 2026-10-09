#ifndef HAMLAB_CURVES_STORE_H
#define HAMLAB_CURVES_STORE_H
#include "curves_core.h"
int hamlab_curves_init(void);
const struct curve_data *hamlab_curve(enum curve_id id);
bool hamlab_curves_from_flash(void);
int hamlab_curves_storage_error(void);
size_t hamlab_curves_expected(void);
size_t hamlab_curves_received(void);
int hamlab_curves_begin(size_t len);
int hamlab_curves_chunk(const char *hex);
void hamlab_curves_abort(void);
int hamlab_curves_check(char *error,size_t len);
int hamlab_curves_import(char *error,size_t len);
int hamlab_curves_export(const char **json);
#define CURVES_PROFILE_NAME 24
#define CURVES_PROFILES_MAX 8
bool hamlab_profile_name_valid(const char *name);
bool hamlab_curves_has_legacy(void);
unsigned hamlab_profiles_count(void);
const char *hamlab_profile_name(unsigned index);
const char *hamlab_curve_profile(enum curve_id id);
int hamlab_curves_import_profile(const char *name,char *error,size_t len);
int hamlab_curves_select(enum curve_id id,const char *name);
#endif
