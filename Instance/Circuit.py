import os
import re
import shutil
import subprocess
import numpy as np


class Circuit:
    def __init__(self, design_dim: int, spec_names: tuple, run_name="", deck_path="input/deck", deck_imports=()):
        self.temp_folder = f"temp_{run_name}" if run_name != "" else "temp"
        self.deck_path = deck_path
        self.simulator = "ngspice_con.exe" if os.name == "nt" else "ngspice"

        self.design_dim = design_dim        
        self.spec_names = spec_names
        self.spec_dim = len(spec_names)
        self.batch_size = 0

        self.design_batch = None
        self.target_spec = np.zeros(self.spec_dim, dtype=np.float64)
        self.pre_weight = np.zeros(self.spec_dim, dtype=np.float64)
        self.post_weight = np.zeros(self.spec_dim, dtype=np.float64)

        shutil.rmtree(self.temp_folder, ignore_errors=True)
        os.makedirs(self.temp_folder)
        os.makedirs(os.path.join(self.temp_folder, "error"))
        for path in deck_imports:
            shutil.copyfile(path, os.path.join(self.temp_folder, os.path.basename(path)))


    def writeCircuit(self, folder): raise NotImplementedError
    def evaluateSpec(self, i, folder): raise NotImplementedError

    def simulateCircuit(self, i):
        subprocess.Popen(
            (self.simulator, "-b", str(i)),
            cwd=self.temp_folder,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).wait()

    def testDeck(self): raise NotImplementedError
    def reserveDesignBatch(self): raise NotImplementedError             

    def evaluateDesign(self):
        self.reserveDesignBatch()    
        self.setSizeFromDesignBatch()        
        self.writeCircuit(self.temp_folder)
        self.renormalizeDesignBatch()
        for i in range(self.batch_size):
            self.simulateCircuit(i)
            self.evaluateSpec(i, self.temp_folder)    
        self.calculateFoM()

    def setTargetSpec(self, target_spec):
        self.target_spec[:] = target_spec
        target_spec = ", ".join(f"{name}: {value}" for name, value in zip(self.spec_names, self.target_spec))
        print(f"Target Spec: {target_spec}")

    def setPreWeight(self, weight):
        self.pre_weight[:] = weight
        weight_spec = ", ".join(f"{name}: {value}" for name, value in zip(self.spec_names, self.pre_weight))
        print(f"Pre-Weight: {weight_spec}")

    def setPostWeight(self, weight):
        self.post_weight[:] = weight
        weight_spec = ", ".join(f"{name}: {value}" for name, value in zip(self.spec_names, self.post_weight))
        print(f"Post-Weight: {weight_spec}")

    def calculateFoM(self): # Every spec is assumed to be maximized.
        # Pre-FoM: Constraint satisfaction while any spec is unmet.
        margins = self.spec_batch - self.target_spec
        self.fom_batch = np.minimum(margins, 0.0) @ self.pre_weight

        # Post-FoM: User-defined design objective after constraint satisfaction.
        zero_fom = (self.fom_batch == 0.0)
        self.fom_batch[zero_fom] = margins[zero_fom] @ self.post_weight      
