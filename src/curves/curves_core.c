/* Bounded JSON parser for schema 1. No heap, no tokens array, no recursion.
 * All four existing channels/frequencies must be supplied as one complete set. */
#include "curves_core.h"
#include <errno.h>
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
const char *const curve_names[]={"forward","reverse_7mhz","reverse_50mhz","current"};
const char *const curve_inputs[]={"A0-A3","A1-A3","A1-A3","A2-A3"};
const char *const curve_references[]={"scope_vpp_sine_50ohm","reversed_coupler_scope_vpp_50ohm","reversed_coupler_scope_vpp_50ohm","a0_master_50ohm"};
const uint32_t curve_frequencies[]={7031670,7100000,50100000,7100000};
const char *curve_reference(enum curve_id id,uint32_t hz){return id==CURVE_CURRENT&&hz==1000000?"scope_vpp_sine_50ohm":curve_references[id];}
const char *curve_master(enum curve_id id,uint32_t hz){return id==CURVE_CURRENT&&hz==7100000?"A0":"scope";}
static bool frequency_valid(int id,double hz){return hz==curve_frequencies[id]||(id==CURVE_CURRENT&&hz==1000000);}
struct parser {const char *start,*p,*end; const char *why;};
static void ws(struct parser *p){while(p->p<p->end&&*p->p&&strchr(" \r\n\t",*p->p))p->p++;}
static int fail(struct parser *p,const char *why){p->why=why;return -EINVAL;}
static int token(struct parser *p,char c){ws(p);if(p->p==p->end||*p->p!=c)return fail(p,"unexpected JSON token");p->p++;return 0;}
static bool next(struct parser *p,char c){ws(p);return p->p<p->end&&*p->p==c;}
static int string(struct parser *p,char *out,size_t len){
    if(token(p,'"'))return -EINVAL;
    size_t n=0;
    while(p->p<p->end&&*p->p!='"'){
        unsigned char c=*p->p++;
        if(c<32||c>=127||c=='\\'||n+1>=len)return fail(p,"invalid/too long schema string");
        out[n++]=(char)c;
    }
    if(p->p==p->end)return fail(p,"unterminated string");
    p->p++;out[n]=0;return 0;
}
static int number(struct parser *p,double *out){
    ws(p);const char *start=p->p;
    if(p->p<p->end&&*p->p=='-')p->p++;
    if(p->p==p->end)return fail(p,"number missing");
    if(*p->p=='0')p->p++;
    else {
        if(*p->p<'1'||*p->p>'9')return fail(p,"invalid JSON number");
        while(p->p<p->end&&isdigit((unsigned char)*p->p))p->p++;
    }
    if(p->p<p->end&&*p->p=='.'){
        p->p++;const char *digits=p->p;
        while(p->p<p->end&&isdigit((unsigned char)*p->p))p->p++;
        if(p->p==digits)return fail(p,"decimal digits missing");
    }
    if(p->p<p->end&&(*p->p=='e'||*p->p=='E')){
        p->p++;if(p->p<p->end&&(*p->p=='+'||*p->p=='-'))p->p++;
        const char *digits=p->p;
        while(p->p<p->end&&isdigit((unsigned char)*p->p))p->p++;
        if(p->p==digits)return fail(p,"exponent digits missing");
    }
    size_t n=(size_t)(p->p-start);char text[48];
    if(n>=sizeof(text))return fail(p,"number too long");
    memcpy(text,start,n);text[n]=0;char *end;errno=0;*out=strtod(text,&end);
    if(errno||*end||!isfinite(*out))return fail(p,"nonfinite/out-of-range number");
    return 0;
}
static bool valid_curve(const struct curve_data *c,int id){
    if(!frequency_valid(id,c->frequency_hz)||c->reserved||c->count<2||c->count>CURVES_POINTS)return false;
    for(unsigned i=0;i<c->count;i++){
        double v=c->points[i].v,w=c->points[i].w;
        if(!isfinite(v)||!isfinite(w)||v<0||v>3.3||w<=0||w>150)return false;
        if(i&&(v<=c->points[i-1].v||w<c->points[i-1].w))return false;
    }
    return true;
}
uint32_t curves_crc(const struct curve_bank *bank){
    uint32_t crc=~0U;const unsigned char *data=(const unsigned char *)bank;
    for(size_t i=0;i<offsetof(struct curve_bank,crc);i++){
        crc^=data[i];for(int bit=0;bit<8;bit++)crc=(crc>>1)^((0U-(crc&1U))&0xedb88320U);
    }
    return ~crc;
}
bool curves_bank_valid(const struct curve_bank *bank){
    if(bank->magic!=CURVES_MAGIC||bank->schema!=CURVES_SCHEMA||bank->crc!=curves_crc(bank))return false;
    for(int i=0;i<CURVES_COUNT;i++)if(!valid_curve(&bank->curves[i],i))return false;
    return true;
}
static int points(struct parser *p,struct curve_data *c){
    if(token(p,'['))return -EINVAL;
    c->count=0;
    if(next(p,']'))return fail(p,"points missing");
    do {
        if(c->count==CURVES_POINTS)return fail(p,"more than 24 points");
        struct curve_point *v=&c->points[c->count++];
        if(token(p,'[')||number(p,&v->v)||token(p,',')||number(p,&v->w)||token(p,']'))return -EINVAL;
        if(next(p,']'))break;
        if(token(p,','))return -EINVAL;
    }while(true);
    return token(p,']');
}
static int curve(struct parser *p,struct curve_bank *bank,unsigned *seen){
    /* One curve uses the unoccupied slot indexed by current list position as scratch.
     * Afterwards the caller reorders all curves by the captured id. */
    unsigned index=0;while(index<CURVES_COUNT&&(*seen&(1U<<index)))index++;
    if(index==CURVES_COUNT)return fail(p,"more than four curves");
    struct curve_data *c=&bank->curves[index];
    char id[24]="",input[16]="",reference[48]="",master[16]="";
    unsigned fields=0;double frequency=0,load=0;
    if(token(p,'{'))return -EINVAL;
    do {
        char key[32];if(string(p,key,sizeof(key))||token(p,':'))return -EINVAL;
        unsigned bit;
        if(!strcmp(key,"id"))bit=1;
        else if(!strcmp(key,"input"))bit=2;
        else if(!strcmp(key,"frequency_hz"))bit=4;
        else if(!strcmp(key,"reference"))bit=8;
        else if(!strcmp(key,"master"))bit=16;
        else if(!strcmp(key,"load_ohms"))bit=32;
        else if(!strcmp(key,"points"))bit=64;
        else return fail(p,"unknown curve field");
        if(fields&bit)return fail(p,"duplicate curve field");
        fields|=bit;
        int rc=0;
        switch(bit){
        case 1:rc=string(p,id,sizeof(id));break;
        case 2:rc=string(p,input,sizeof(input));break;
        case 4:rc=number(p,&frequency);break;
        case 8:rc=string(p,reference,sizeof(reference));break;
        case 16:rc=string(p,master,sizeof(master));break;
        case 32:rc=number(p,&load);break;
        case 64:rc=points(p,c);break;
        }
        if(rc)return rc;
        if(next(p,'}'))break;
        if(token(p,','))return -EINVAL;
    }while(true);
    if(token(p,'}'))return -EINVAL;
    if(fields!=127)return fail(p,"curve field missing");
    int actual=-1;for(int i=0;i<CURVES_COUNT;i++)if(!strcmp(id,curve_names[i]))actual=i;
    if(actual<0||!frequency_valid(actual,frequency)||strcmp(input,curve_inputs[actual])||
       strcmp(reference,curve_reference(actual,(uint32_t)frequency))||strcmp(master,curve_master(actual,(uint32_t)frequency))||load!=50)
        return fail(p,"unsupported curve id/input/frequency/reference/master/load");
    /* reserved temporarily holds the id; strict validation follows after sorting. */
    c->frequency_hz=(uint32_t)frequency;c->reserved=(uint16_t)actual;
    *seen|=1U<<index;
    return 0;
}
int curves_parse(const char *json,size_t len,struct curve_bank *out,char *error,size_t error_len){
    if(error_len)error[0]=0;
    if(!json||!len||len>CURVES_JSON_MAX){if(error_len)snprintf(error,error_len,"JSON length must be 1..4096");return -EINVAL;}
    memset(out,0,sizeof(*out));struct parser p={json,json,json+len,NULL};unsigned fields=0,seen=0;double schema=0;
    if(token(&p,'{'))goto bad;
    do {
        char key[32];if(string(&p,key,sizeof(key))||token(&p,':'))goto bad;
        unsigned bit=!strcmp(key,"schema_version")?1:!strcmp(key,"curves")?2:0;
        if(!bit){fail(&p,"unknown root field");goto bad;}
        if(fields&bit){fail(&p,"duplicate root field");goto bad;}fields|=bit;
        if(bit==1){if(number(&p,&schema))goto bad;}
        else {
            if(token(&p,'['))goto bad;
            do {if(curve(&p,out,&seen))goto bad;if(next(&p,']'))break;if(token(&p,','))goto bad;}while(true);
            if(token(&p,']'))goto bad;
        }
        if(next(&p,'}'))break;
        if(token(&p,','))goto bad;
    }while(true);
    if(token(&p,'}'))goto bad;
    ws(&p);if(p.p!=p.end){fail(&p,"trailing JSON data");goto bad;}
    if(fields!=3||schema!=CURVES_SCHEMA||seen!=15){fail(&p,"schema 1 and all four curves required");goto bad;}
    unsigned ids=0;
    for(int i=0;i<CURVES_COUNT;i++){
        unsigned id=out->curves[i].reserved;
        if(ids&(1U<<id)){fail(&p,"duplicate curve id");goto bad;}ids|=1U<<id;
    }
    /* Swap into canonical order, only one small point array on stack. */
    for(int i=0;i<CURVES_COUNT;i++){
        int j=i;while(j<CURVES_COUNT&&out->curves[j].reserved!=i)j++;
        if(j!=i){struct curve_data tmp=out->curves[i];out->curves[i]=out->curves[j];out->curves[j]=tmp;}
    }
    for(int i=0;i<CURVES_COUNT;i++){
        out->curves[i].reserved=0;
        if(!valid_curve(&out->curves[i],i)){fail(&p,"invalid limits/order: 2..24 points, 0..3.3 V, 0<W<=150, V increasing, W nondecreasing");goto bad;}
    }
    out->magic=CURVES_MAGIC;out->schema=CURVES_SCHEMA;out->crc=curves_crc(out);return 0;
 bad:
    if(error_len)snprintf(error,error_len,"%s at byte %zu",p.why?p.why:"invalid JSON",(size_t)(p.p-p.start));
    return -EINVAL;
}
bool curves_interpolate(const struct curve_data *c,double v,double *w){
    if(!isfinite(v)||c->count<2||v<c->points[0].v||v>c->points[c->count-1].v)return false;
    for(unsigned i=1;i<c->count;i++)if(v<=c->points[i].v){
        double t=(v-c->points[i-1].v)/(c->points[i].v-c->points[i-1].v);
        *w=c->points[i-1].w+t*(c->points[i].w-c->points[i-1].w);return true;
    }
    return false;
}
static int append(char *out,size_t len,size_t *used,const char *format,...){
    if(*used>=len)return -ENOSPC;
    va_list ap;va_start(ap,format);int n=vsnprintf(out?out+*used:NULL,out?len-*used:0,format,ap);va_end(ap);
    if(n<0||(size_t)n>=len-*used)return -ENOSPC;
    *used+=(size_t)n;return 0;
}
int curves_encode(const struct curve_bank *bank,char *out,size_t len){
    size_t n=0;
    if(append(out,len,&n,"{\"schema_version\":1,\"curves\":["))return -ENOSPC;
    for(int i=0;i<CURVES_COUNT;i++){
        const struct curve_data *c=&bank->curves[i];
        if(append(out,len,&n,"%s{\"id\":\"%s\",\"input\":\"%s\",\"frequency_hz\":%u,\"reference\":\"%s\",\"master\":\"%s\",\"load_ohms\":50,\"points\":[",i?",":"",curve_names[i],curve_inputs[i],c->frequency_hz,curve_reference(i,c->frequency_hz),curve_master(i,c->frequency_hz)))return -ENOSPC;
        for(unsigned j=0;j<c->count;j++)if(append(out,len,&n,"%s[%.17g,%.17g]",j?",":"",c->points[j].v,c->points[j].w))return -ENOSPC;
        if(append(out,len,&n,"]}"))return -ENOSPC;
    }
    if(append(out,len,&n,"]}"))return -ENOSPC;
    return (int)n;
}
