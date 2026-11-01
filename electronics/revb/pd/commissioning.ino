// Factory fixture only. NOT normal feeder firmware; do not write NVM on each boot.
// SparkFun_STUSB4500_Arduino_Library documented public API.
// Hardware: disconnect USB cable; feed 5V current-limited at PD_VBUS_RAW and GND;
// fixture shorts TP203(PD_GATE) to TP204(PD_FET_SOURCE) to force both FETs OFF.
// Supply host +3V3 independently and use HOST_SCL/HOST_SDA (through U203).
// The current design has VSYS grounded: supplying host +3V3 alone will NOT program it.
#include <Wire.h>
#include <SparkFun_STUSB4500.h>

STUSB4500 pd;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(100000);
  delay(100); // ST TLOAD <=30ms, allow supplies to settle.
  if (!pd.begin(0x28, Wire)) {
    Serial.println("FAIL: no STUSB4500; stop fixture");
    return;
  }
  pd.setPdoNumber(2);
  pd.setCurrent(1, 0.5);
  for (uint8_t pdo = 2; pdo <= 3; ++pdo) {
    pd.setVoltage(pdo, 20.0);
    pd.setCurrent(pdo, 5.0);
    pd.setLowerVoltageLimit(pdo, 10);
    pd.setUpperVoltageLimit(pdo, 5);
  }
  pd.setPowerAbove5vOnly(1);
  pd.setConfigOkGpio(2);
  pd.setGpioCtrl(1);
  pd.setExternalPower(0);
  pd.setUsbCommCapable(0);
  pd.setReqSrcCurrent(0);
  pd.write();
  pd.read();
  const bool ok = pd.getPdoNumber() == 2 && pd.getVoltage(2) == 20.0 &&
      pd.getCurrent(2) == 5.0 && pd.getPowerAbove5vOnly() == 1 &&
      pd.getConfigOkGpio() == 2 && pd.getReqSrcCurrent() == 0 &&
      pd.getLowerVoltageLimit(2) == 10 && pd.getUpperVoltageLimit(2) == 5;
  Serial.println(ok ? "READBACK OK; cold power-cycle and PD analyzer tests still required"
                    : "FAIL NVM readback; do not release");
  // SparkFun API does not expose all discharge NVM fields here. Preserve factory
  // calibration/reserved bits; separately verify DISCH_DISABLE=0 and timings 9/12
  // with ST's official NVM tool/readout before release. No binary image invented.
}

void loop() {}
