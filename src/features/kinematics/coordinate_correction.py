import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import griddata

_CSV_PATH = Path(__file__).parents[3] / "src" / "resources" / "tabla_compensacion" / "datos_robot.csv"
_df_cache = None


def _load_data():
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(_CSV_PATH, sep=';')
    return _df_cache


def corregir_xy(x_objetivo, y_objetivo):
    df = _load_data()
    x_d = df['X_deseado mm'].values
    y_d = df['Y_deseado mm'].values
    e_x = df['error X mm'].values
    e_y = df['error Y mm'].values

    delta_x = griddata((x_d, y_d), e_x, (x_objetivo, y_objetivo), method='linear')
    delta_y = griddata((x_d, y_d), e_y, (x_objetivo, y_objetivo), method='linear')

    delta_x = 0 if np.isnan(delta_x) else delta_x
    delta_y = 0 if np.isnan(delta_y) else delta_y

    return round(x_objetivo + delta_x), round(y_objetivo + delta_y)


def corregir_z(x_objetivo, y_objetivo, z_objetivo):
    radio = math.sqrt(x_objetivo**2 + y_objetivo**2)
    errorz = 0.0007 * radio**2 - 0.1316 * radio + 14.694
    return round(z_objetivo + errorz)
