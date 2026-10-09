#ifndef CURRENT_CALIBRATION_H
#define CURRENT_CALIBRATION_H
#include <math.h>
#include <stdbool.h>
#include <stddef.h>
#include "curves/curves_store.h"
/* Paired A0 master / A2 measurements, 2026-10-06, 7.1 MHz.
 * A0 watts are the reference, not ICOM percentage or former scope curve.
 * 1 percent excluded: A0 below calibrated floor. 90/100 percent pooled:
 * indistinguishable A2 voltage within sample scatter. Endpoint guards cover
 * only observed endpoint sample voltages, with constant endpoint watts.
 * Resistive 50 ohms ONLY. No extrapolation outside measured voltage bounds. */
#define CURRENT_CALIBRATION_HZ 7100000U
#define CURRENT_MIN_W (hamlab_curve(CURVE_CURRENT)->points[0].w)
#define CURRENT_MAX_W (current_max_w())
#define CURRENT_PLATEAU_V (current_plateau_v())
static const __attribute__((unused)) struct {double v,w;} current_curve[]={
    {0.019687500000,1.494300000000},
    {0.019713566667,1.494300000000},
    {0.039494800000,2.104700000000},
    {0.056960933333,2.586900000000},
    {0.086549466667,3.726366666667},
    {0.243015633333,10.410466666667},
    {0.281750000000,12.822733333333},
    {0.321697900000,16.678633333333},
    {0.385187500000,25.142500000000},
    {0.436041666667,35.765400000000},
    {0.479604166667,47.222500000000},
    {0.502822933333,55.466933333333},
    {0.525354166667,65.059266666667},
    {0.543625000000,74.074366666667},
    {0.558520816667,83.346166666667},
    {0.560062500000,83.346166666667},
};
static inline double current_max_w(void){const struct curve_data *c=hamlab_curve(CURVE_CURRENT);return c->points[c->count-1].w;}
static inline double current_plateau_v(void){
    const struct curve_data *c=hamlab_curve(CURVE_CURRENT);size_t i=c->count-1;
    while(i>0&&c->points[i-1].w==c->points[c->count-1].w)i--;
    return c->points[i].v;
}
static inline bool current_power(double v,double *w){
    return curves_interpolate(hamlab_curve(CURVE_CURRENT),v,w);
}
#endif
