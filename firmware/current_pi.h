#ifndef CURRENT_PI_H
#define CURRENT_PI_H

typedef struct {
    float kp;
    float ki;
    float dt;
    float out_min;
    float out_max;
    float integ;
} pi_t;

void  pi_init(pi_t *c, float kp, float ki, float dt,
              float out_min, float out_max);
float pi_update(pi_t *c, float setpoint_A, float measured_A);
void  pi_reset(pi_t *c);

#endif
