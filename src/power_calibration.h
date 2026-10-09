#ifndef POWER_CALIBRATION_H
#define POWER_CALIBRATION_H
#include <stdbool.h>
#include <stddef.h>
#include <math.h>
#include "curves/curves_store.h"
/* ADC-side voltages, divider included. Scope sine Vpp^2/(8*50).
 * Provisional, ONLY measured at 7031670 Hz. No extrapolation or zero anchor. */
static const __attribute__((unused)) struct { double v, w; } forward_curve[] = {
    {0.0556641,1.2544},
    {0.0860469,1.6384},
    {0.1380937,2.2500},
    {0.1790000,2.7556},
    {0.2404375,4.0000},
    {0.5645938,10.7584},
    {0.6690312,13.2496},
    {0.7982813,17.3056},
    {1.0539375,26.0100},
    {1.3049375,37.2100},
    {1.5681875,49.0000},
    {1.7332500,57.7600},
    {1.8861250,67.2400},
    {2.0262500,75.6900},
    {2.1535000,84.6400},
    {2.2778750,92.1600},
};
static inline bool forward_power(double v, double *w) {
    return curves_interpolate(hamlab_curve(CURVE_FORWARD),v,w);
}
/* Reversed coupler, 50-ohm reference, averaged/pooled repetitions.
 * Runtime selection is RAM-only. No automatic RF frequency detection. */
static unsigned int reverse_calibration_hz=7100000;
struct reverse_cal_point { double v,w; };
static const __attribute__((unused)) struct reverse_cal_point reverse_curve_7100000[]={
    {0.0530182333,1.3456000000},
    {0.0829349000,1.7424000000},
    {0.1362760333,2.4336000000},
    {0.2390937333,3.9469333333},
    {0.5619895667,11.6512000000},
    {0.6655833333,14.5418666667},
    {0.7942083667,18.4330666667},
    {1.0455833333,29.5233333333},
    {1.2900625000,39.6900000000},
    {1.5458750000,53.7800000000},
    {1.7054166667,61.8866666667},
    {1.8639166667,72.8200000000},
    {1.9976250000,82.8100000000},
    {2.0872083333,88.9900000000},
};
static const __attribute__((unused)) struct reverse_cal_point reverse_curve_50100000[]={
    {0.0249869667,1.1096000000},
    {0.0444479333,1.3768000000},
    {0.0852552000,1.9790666667},
    {0.1664192667,3.1450666667},
    {0.4418229333,9.2426666667},
    {0.5395625000,11.9258666667},
    {0.6560625000,15.4736000000},
    {0.9020000000,25.6733333333},
    {1.1729375000,38.4400000000},
    {1.4391458333,52.8066666667},
    {1.5773958333,62.4100000000},
    {1.6880000000,68.8966666667},
    {1.6989166667,70.0100000000},
    {1.7051250000,70.5600000000},
};
static inline enum curve_id reverse_id(void){return reverse_calibration_hz==50100000?CURVE_REVERSE_50:CURVE_REVERSE_7;}
static inline double reverse_min_v(void){return hamlab_curve(reverse_id())->points[0].v;}
static inline double reverse_min_w(void){return hamlab_curve(reverse_id())->points[0].w;}
static inline double reverse_max_w(void){const struct curve_data *c=hamlab_curve(reverse_id());return c->points[c->count-1].w;}
static inline bool swr_calibration_compatible(void){return reverse_calibration_hz==7100000;}
static inline bool reverse_power(double v,double *w){return curves_interpolate(hamlab_curve(reverse_id()),v,w);}
static inline bool calibrated_swr(double pf,double pr,double *swr){
    if(!isfinite(pf)||!isfinite(pr)||pf<=0||pr<0||pr>=pf)return false;
    double rho=sqrt(pr/pf);*swr=(1+rho)/(1-rho);return isfinite(*swr);
}
#endif
