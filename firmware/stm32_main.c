#include "stm32l4xx_hal.h"
#include "current_pi.h"
#include <stdlib.h>
#include <string.h>

#define VBAT_V        6.0f
#define SHUNT_OHM     0.1f
#define AMP_GAIN      11.0f
#define ADC_FS_V      3.3f
#define ADC_FS_CNT    4095.0f
#define DT_S          0.001f
#define WC_RAD        628.3f
#define R_MOTOR       4.0f
#define L_MOTOR       2e-3f
#define FAILSAFE_MS   200
#define DUTY_MAX      0.95f

extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern ADC_HandleTypeDef hadc1;
extern UART_HandleTypeDef huart1;

static pi_t pi;
static volatile float    setpoint_A = 0.0f;
static volatile uint32_t last_rx_ms = 0;
static volatile int      dir = 1;

static uint8_t rx_byte;
static char    line[16];
static int     line_n = 0;

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *h)
{
    if (h != &huart1) return;
    char c = (char)rx_byte;
    if (c == '\n' || c == '\r') {
        if (line_n > 1 && line[0] == 'C') {
            line[line_n] = '\0';
            setpoint_A = (float)atoi(&line[1]) / 1000.0f;
            last_rx_ms = HAL_GetTick();
        }
        line_n = 0;
    } else if (line_n < (int)sizeof(line) - 1) {
        line[line_n++] = c;
    }
    HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
}

static float read_current_A(void)
{
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 1);
    float counts = (float)HAL_ADC_GetValue(&hadc1);
    float amps = counts * ADC_FS_V / ADC_FS_CNT / (SHUNT_OHM * AMP_GAIN);
    return (dir >= 0) ? amps : -amps;
}

static void bridge_set(float u_volts)
{
    float duty = u_volts / VBAT_V;
    if (duty >  DUTY_MAX) duty =  DUTY_MAX;
    if (duty < -DUTY_MAX) duty = -DUTY_MAX;
    dir = (duty >= 0.0f) ? 1 : -1;
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
    uint32_t ccr = (uint32_t)((duty >= 0 ? duty : -duty) * (float)arr);
    if (dir >= 0) {
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr);
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0);
    } else {
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, ccr);
    }
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *h)
{
    if (h != &htim2) return;

    float sp = setpoint_A;
    if (HAL_GetTick() - last_rx_ms > FAILSAFE_MS) {
        sp = 0.0f;
        pi_reset(&pi);
    }
    float i_meas = read_current_A();
    float u = pi_update(&pi, sp, i_meas);
    bridge_set(u);
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM1_Init();
    MX_TIM2_Init();
    MX_ADC1_Init();
    MX_USART1_UART_Init();

    pi_init(&pi, L_MOTOR * WC_RAD, R_MOTOR * WC_RAD, DT_S, -VBAT_V, VBAT_V);

    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
    HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
    HAL_TIM_Base_Start_IT(&htim2);

    while (1) { __WFI(); }
}
