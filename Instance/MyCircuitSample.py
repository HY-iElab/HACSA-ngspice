import numpy as np
from .Circuit import Circuit as _Circuit


class MyCircuit(_Circuit):
    def __init__(self, run_name='', deck_path="input/deck"):
        spec_names = ("negative_total_current_uA", "gain_db", "log10_ugbw", "pm_deg", "cmrr_db")
        self.NUM_RESISTOR = 2
        self.NUM_CAPACITOR = 3
        self.NUM_MOSFET = 13
        design_dim = self.NUM_RESISTOR + self.NUM_CAPACITOR + 3 * self.NUM_MOSFET
        super().__init__(design_dim, spec_names, run_name=run_name, deck_path=deck_path)

    def setSizeFromDesignBatch(self):
        size = self.design_batch[: self.batch_size]
        r_end = self.NUM_RESISTOR
        c_end = r_end + self.NUM_CAPACITOR
        l_end = c_end + self.NUM_MOSFET
        w_end = l_end + self.NUM_MOSFET

        self.r = 10.0 ** (size[:, :r_end] * 3.0 + 3.0) + 5e-4
        self.c = size[:, r_end:c_end] * 990.0 + 10.0 + 5e-4
        self.l = 180 + np.rint(size[:, c_end:l_end] * 36.0).astype(np.int32) * 5
        self.w = 45 + np.rint(size[:, l_end:w_end] * 9.0).astype(np.int32) * 5
        self.m = 1 + np.rint(size[:, w_end:] * 59.0).astype(np.int32)

    def renormalizeDesignBatch(self):
        size = self.design_batch[: self.batch_size]
        offset = self.NUM_RESISTOR + self.NUM_CAPACITOR
        size[:, offset : offset + self.NUM_MOSFET] = (self.l - 180) / 180.0
        size[:, offset + self.NUM_MOSFET : offset + 2 * self.NUM_MOSFET] = (self.w - 45) / 45.0
        size[:, offset + 2 * self.NUM_MOSFET :] = (self.m - 1) / 59.0

    def writeCircuit(self, folder="temp"):
        for i in range(self.batch_size):
            with open(f"{folder}/param_{i}", "w") as file:
                for j in range(self.NUM_RESISTOR):
                    file.write(f".param R{j}={self.r[i,j]:.3f}\n")
                for j in range(self.NUM_CAPACITOR):
                    file.write(f".param C{j}={self.c[i,j]:.3f}f\n")
                for j in range(self.NUM_MOSFET):
                    file.write(
                        f".param L{j}={self.l[i,j]}n\n"
                        f".param W{j}={self.w[i,j]}n\n"
                        f".param M{j}={self.m[i,j]}\n"
                    )

    def evaluateSpec(self, i, folder="temp"):
        self.spec_batch[i] = np.loadtxt(
            f"{folder}/spec_{i}",
            dtype=np.float64,
            usecols=1,
            max_rows=self.spec_dim,
            ndmin=1,
        )        
