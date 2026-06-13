#include "current_pi.h"

void pi_init(pi_t *c, float kp, float ki, float dt,
             float out_min, float out_max)
{
    c->kp = kp;  c->ki = ki;  c->dt = dt;
    c->out_min = out_min;  c->out_max = out_max;
    c->integ = 0.0f;
}

void pi_reset(pi_t *c) { c->integ = 0.0f; }

float pi_update(pi_t *c, float setpoint_A, float measured_A)
{
    float e = setpoint_A - measured_A;
    float u_unsat = c->kp * e + c->integ;

    float u = u_unsat;
    if (u > c->out_max) u = c->out_max;
    if (u < c->out_min) u = c->out_min;

    int sat_hi = (u_unsat > c->out_max) && (e > 0.0f);
    int sat_lo = (u_unsat < c->out_min) && (e < 0.0f);
    if (!sat_hi && !sat_lo) {
        c->integ += c->ki * e * c->dt;
        if (c->integ > c->out_max) c->integ = c->out_max;
        if (c->integ < c->out_min) c->integ = c->out_min;
    }
    return u;
}
