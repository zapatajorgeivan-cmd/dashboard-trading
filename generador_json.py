import pandas as pd
import os
import glob
import json

carpeta_origen = 'archivos_originales' 
carpeta_destino = 'datos'              
os.makedirs(carpeta_destino, exist_ok=True)
archivos = glob.glob(os.path.join(carpeta_origen, '*.xlsx'))
capital_inicial = 10000

for archivo in archivos:
    try:
        nombre_base = os.path.basename(archivo)
        codigo = nombre_base.replace('DATA ', '').replace('.xlsx', '').strip()
        print(f"Procesando: {codigo}")
        
        df = pd.read_excel(archivo, sheet_name='Trades')
        df.columns = df.columns.str.strip()
        
        df = df[df['Tipo'].astype(str).str.contains('Salida', case=False, na=False)].copy()
        df['Fecha'] = pd.to_datetime(df['Fecha y hora'])
        df['Equity'] = capital_inicial + pd.to_numeric(df['Cumulative PnL USDT'], errors='coerce')
        df['Pico'] = df['Equity'].cummax()
        df['DD %'] = ((df['Equity'] / df['Pico']) - 1) * 100
        
        rent_media = df['Net PnL %'].mean()
        std_dev = df['Net PnL %'].std()
        sharpe = (rent_media / std_dev) if std_dev != 0 else 0
        
        g_bruta = df[df['Net PnL USDT'] > 0]['Net PnL USDT'].sum()
        p_bruta = abs(df[df['Net PnL USDT'] < 0]['Net PnL USDT'].sum())
        p_factor = g_bruta / p_bruta if p_bruta != 0 else g_bruta
        
        mdd = abs(df['DD %'].min())
        calmar = (rent_media * 52) / mdd if mdd != 0 else 0
        
        df.set_index('Fecha', inplace=True)
        df_semanal = df['DD %'].resample('W').min().dropna()
        
        data = {
            "fechas": df_semanal.index.strftime('%b %y').tolist(),
            "drawdown": [round(float(v), 2) for v in df_semanal.values],
            "metricas": {"sharpe": round(sharpe, 2), "profit_factor": round(p_factor, 2), "calmar": round(calmar, 2)}
        }
        
        with open(os.path.join(carpeta_destino, f"{codigo}.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
    except Exception as e:
        print(f"Error en {codigo}: {e}")

print("¡PROCESO FINALIZADO!")
