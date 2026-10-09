#include "curves_store.h"
#include <zephyr/settings/settings.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include "curve_defaults.inc"
/* Shared only under application's measurement mutex; no heap allocation. */
static int storage_error;
static struct curve_bank active,candidate;
static char profiles[CURVES_PROFILES_MAX][CURVES_PROFILE_NAME];
static unsigned profile_count;
static bool legacy_present;
static char selected[CURVES_COUNT][CURVES_PROFILE_NAME];
struct snapshot {struct curve_bank bank;char selected[CURVES_COUNT][CURVES_PROFILE_NAME];uint32_t crc;};
static struct snapshot snapshot;
static uint32_t snapshot_crc(void){
    const unsigned char *data=(const unsigned char *)&snapshot;uint32_t crc=~0U;
    for(size_t i=0;i<offsetof(struct snapshot,crc);i++){
        crc^=data[i];for(int b=0;b<8;b++)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
    }
    return ~crc;
}
bool hamlab_profile_name_valid(const char *name){
    size_t n=strlen(name);if(!n||n>=CURVES_PROFILE_NAME)return false;
    for(size_t i=0;i<n;i++)if(!((name[i]>='a'&&name[i]<='z')||(name[i]>='A'&&name[i]<='Z')||(name[i]>='0'&&name[i]<='9')||name[i]=='_'||name[i]=='-'))return false;
    return strcmp(name,"builtin")&&strcmp(name,"legacy")&&strcmp(name,"imported")&&strcmp(name,"active");
}
static bool selection_name_valid(const char *name){return !strcmp(name,"builtin")||!strcmp(name,"legacy")||!strcmp(name,"imported")||hamlab_profile_name_valid(name);}
bool hamlab_curves_has_legacy(void){return legacy_present;}
unsigned hamlab_profiles_count(void){return profile_count;}
const char *hamlab_profile_name(unsigned i){return i<profile_count?profiles[i]:"";}
const char *hamlab_curve_profile(enum curve_id id){return selected[id];}
static int profile_index(const char *name){for(unsigned i=0;i<profile_count;i++)if(!strcmp(name,profiles[i]))return (int)i;return -1;}
static int save_snapshot(const struct curve_bank *bank,const char names[CURVES_COUNT][CURVES_PROFILE_NAME]){
    memset(&snapshot,0,sizeof(snapshot));snapshot.bank=*bank;
    memcpy(snapshot.selected,names,sizeof(snapshot.selected));snapshot.crc=snapshot_crc();
    int rc=settings_save_one("hamlab_profiles/active",&snapshot,sizeof(snapshot));
    if(rc)storage_error=rc;
    return rc;
}
static char staging[CURVES_JSON_MAX+1];
static size_t expected,received;
static bool from_flash,storage_ready;
static int load_bank(const char *key,size_t len,settings_read_cb read_cb,void *cb_arg,void *param){
    (void)param;
    if(strcmp(key,"bank"))return 0;
    if(len!=sizeof(candidate)){storage_error=-EINVAL;return 0;}
    int rc=read_cb(cb_arg,&candidate,sizeof(candidate));
    if(rc!=(int)sizeof(candidate)){storage_error=rc<0?rc:-EIO;return 0;}
    if(!curves_bank_valid(&candidate)){storage_error=-EBADMSG;return 0;}
    active=candidate;from_flash=true;legacy_present=true;for(int i=0;i<CURVES_COUNT;i++)strcpy(selected[i],"legacy");return 0;
}
static int load_profiles(const char *key,size_t len,settings_read_cb read_cb,void *cb_arg,void *param){
    (void)param;
    if(!key)return 0;
    if(!strcmp(key,"active")){
        if(len!=sizeof(snapshot)||read_cb(cb_arg,&snapshot,len)!=(ssize_t)len||!curves_bank_valid(&snapshot.bank)||snapshot.crc!=snapshot_crc()){storage_error=-EBADMSG;return 0;}
        for(int i=0;i<CURVES_COUNT;i++)if(!memchr(snapshot.selected[i],0,CURVES_PROFILE_NAME)||!selection_name_valid(snapshot.selected[i])){storage_error=-EBADMSG;return 0;}
        active=snapshot.bank;memcpy(selected,snapshot.selected,sizeof(selected));from_flash=true;return 0;
    }
    if(!hamlab_profile_name_valid(key))return 0;
    if(len!=sizeof(candidate)||read_cb(cb_arg,&candidate,len)!=(ssize_t)len||!curves_bank_valid(&candidate)){storage_error=-EBADMSG;return 0;}
    if(profile_count<CURVES_PROFILES_MAX)strcpy(profiles[profile_count++],key);
    else storage_error=-ENOSPC;
    return 0;
}
int hamlab_curves_init(void){
    active=builtin_bank;active.crc=curves_crc(&active);from_flash=false;
    storage_ready=false;storage_error=0;profile_count=0;legacy_present=false;hamlab_curves_abort();
    for(int i=0;i<CURVES_COUNT;i++)strcpy(selected[i],"builtin");
    int rc=settings_subsys_init();
    if(rc){storage_error=rc;return rc;}
    storage_ready=true;
    rc=settings_load_subtree_direct("hamlab_curves",load_bank,NULL);
    if(rc)storage_error=rc;
    rc=settings_load_subtree_direct("hamlab_profiles",load_profiles,NULL);
    if(rc)storage_error=rc;
    return storage_error;
}
const struct curve_data *hamlab_curve(enum curve_id id){return &active.curves[id];}
bool hamlab_curves_from_flash(void){return from_flash;}
int hamlab_curves_storage_error(void){return storage_error;}
size_t hamlab_curves_expected(void){return expected;}
size_t hamlab_curves_received(void){return received;}
int hamlab_curves_begin(size_t len){
    if(expected)return -EBUSY;
    if(!len||len>CURVES_JSON_MAX)return -E2BIG;
    expected=len;received=0;staging[0]=0;return 0;
}
static int nibble(char c){
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
}
int hamlab_curves_chunk(const char *hex){
    if(!expected)return -EINVAL;
    size_t n=strlen(hex);
    if(!n||n>160||(n&1)||n/2>expected-received)return -E2BIG;
    /* Validate entire block first; a rejected chunk changes nothing. */
    for(size_t i=0;i<n;i++)if(nibble(hex[i])<0)return -EINVAL;
    for(size_t i=0;i<n;i+=2)staging[received++]=(char)((nibble(hex[i])<<4)|nibble(hex[i+1]));
    staging[received]=0;return 0;
}
void hamlab_curves_abort(void){expected=received=0;staging[0]=0;}
int hamlab_curves_check(char *error,size_t len){
    if(!expected||received!=expected){snprintf(error,len,"transfer incomplete: %zu/%zu bytes",received,expected);return -EINVAL;}
    int rc=curves_parse(staging,received,&candidate,error,len);
    if(!rc&&curves_encode(&candidate,NULL,sizeof(staging))<0){snprintf(error,len,"normalized JSON exceeds 4096 bytes");return -E2BIG;}
    return rc;
}
int hamlab_curves_import(char *error,size_t len){
    int rc=hamlab_curves_check(error,len);if(rc)return rc;
    if(!storage_ready){snprintf(error,len,"settings storage not ready");return -ENODEV;}
    char names[CURVES_COUNT][CURVES_PROFILE_NAME]={{0}};
    for(int i=0;i<CURVES_COUNT;i++)strcpy(names[i],"imported");
    if(!from_flash||memcmp(&candidate,&active,sizeof(active))||memcmp(names,selected,sizeof(selected))){
        rc=save_snapshot(&candidate,names);
        if(rc){snprintf(error,len,"flash save failed: %d; active curves unchanged",rc);return rc;}
    }
    active=candidate;memcpy(selected,names,sizeof(selected));from_flash=true;storage_error=0;hamlab_curves_abort();return 0;
}
int hamlab_curves_import_profile(const char *name,char *error,size_t len){
    if(!hamlab_profile_name_valid(name)){snprintf(error,len,"name: 1..23 letters/digits/_/-, reserved names forbidden");return -EINVAL;}
    int rc=hamlab_curves_check(error,len);if(rc)return rc;
    if(!storage_ready)return -ENODEV;
    int index=profile_index(name);
    if(index<0&&profile_count==CURVES_PROFILES_MAX)return -ENOSPC;
    for(int i=0;i<CURVES_COUNT;i++)if(!strcmp(selected[i],name)){snprintf(error,len,"profile in use; select builtin before replacing");return -EBUSY;}
    char key[48];snprintf(key,sizeof(key),"hamlab_profiles/%s",name);
    rc=settings_save_one(key,&candidate,sizeof(candidate));
    if(rc){storage_error=rc;snprintf(error,len,"flash save failed: %d",rc);return rc;}
    if(index<0)strcpy(profiles[profile_count++],name);
    storage_error=0;hamlab_curves_abort();return 0;
}
struct profile_read {const char *name;int result;};
static int read_profile(const char *key,size_t len,settings_read_cb read_cb,void *cb_arg,void *param){
    struct profile_read *p=param;if(!key||strcmp(key,p->name))return 0;
    if(len!=sizeof(candidate)||read_cb(cb_arg,&candidate,len)!=(ssize_t)len||!curves_bank_valid(&candidate)){p->result=-EBADMSG;return 0;}
    p->result=0;return 0;
}
int hamlab_curves_select(enum curve_id id,const char *name){
    if(id<0||id>=CURVES_COUNT)return -EINVAL;
    if(expected)return -EBUSY;
    if(!storage_ready)return -ENODEV;
    if(!strcmp(name,"builtin"))candidate=builtin_bank;
    else if(!strcmp(name,"legacy")){
        if(!legacy_present)return -ENOENT;
        struct profile_read p={"bank",-ENOENT};
        int rc=settings_load_subtree_direct("hamlab_curves",read_profile,&p);
        if(rc)return rc;
        if(p.result)return p.result;
    }else {
        if(!hamlab_profile_name_valid(name)||profile_index(name)<0)return -ENOENT;
        struct profile_read p={name,-ENOENT};
        int rc=settings_load_subtree_direct("hamlab_profiles",read_profile,&p);
        if(rc)return rc;
        if(p.result)return p.result;
    }
    struct curve_data replacement=candidate.curves[id];candidate=active;candidate.curves[id]=replacement;candidate.crc=curves_crc(&candidate);
    if(curves_encode(&candidate,NULL,sizeof(staging))<0)return -E2BIG;
    char names[CURVES_COUNT][CURVES_PROFILE_NAME];memcpy(names,selected,sizeof(names));memset(names[id],0,sizeof(names[id]));strcpy(names[id],name);
    if(from_flash&&!memcmp(&candidate,&active,sizeof(active))&&!memcmp(names,selected,sizeof(selected)))return 0;
    int rc=save_snapshot(&candidate,names);if(rc)return rc;
    active=candidate;memcpy(selected,names,sizeof(selected));from_flash=true;storage_error=0;return 0;
}
int hamlab_curves_export(const char **json){
    if(expected)return -EBUSY;
    int n=curves_encode(&active,staging,sizeof(staging));
    if(n<0)return n;
    *json=staging;return n;
}
