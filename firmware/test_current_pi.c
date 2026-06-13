#include <stdio.h>
#include "current_pi.h"

int main(void)
{
    const float R = 4.0f, L = 2e-3f;
    const float VBAT = 6.0f;
    const float DT_CTRL  = 1e-3f;
    const float DT_PLANT = 1e-5f;
    const float WC = 2.0f * 3.14159265f * 100.0f;

    pi_t pi;
    pi_init(&pi, L * WC, R * WC, DT_CTRL, -VBAT, VBAT);
    printf("kp = %.3f V/A,  ki = %.1f V/(A s)\n", pi.kp, pi.ki);

    float i = 0.0f;
    float u = 0.0f;
    FILE *f = fopen("pi_log.csv", "w");
    fprintf(f, "t,setpoint,current,voltage\n");

    for (int k = 0; k < 120; k++) {
        float t = k * DT_CTRL;
        float sp = 0.0f;
        if (t >= 0.005f) sp =  0.5f;
        if (t >= 0.040f) sp = -0.3f;
        if (t >= 0.070f) sp =  2.0f;
        if (t >= 0.095f) sp =  0.5f;

        u = pi_update(&pi, sp, i);
        for (int s = 0; s < (int)(DT_CTRL / DT_PLANT + 0.5f); s++)
            i += DT_PLANT * (u - i * R) / L;

        fprintf(f, "%.4f,%.3f,%.4f,%.3f\n", t, sp, i, u);
    }
    fclose(f);
    printf("wrote pi_log.csv\n");
    return 0;
}
