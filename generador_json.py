import pandas as pd
import os
import glob
import json

# 1. Configuración de carpetas
carpeta_origen = 'archivos_originales' 
carpeta_destino = 'datos'              

os.makedirs(carpeta_destino, exist_ok=True)
archivos = glob.glob(os.path.join(carpeta_origen, '*.xlsx'))
capital_inicial = 10000

print(f"Buscando archivos en: {carpeta_origen}...")
print(f"Se encontraron {len(archivos)} archivos.")

for archivo in archivos:
    try:
        nombre_base = os.path.basename(archivo)
        codigo = nombre_base.replace('DATA ', '').replace('.xlsx', '').strip()
        print(f"Procesando: {codigo}...")
        
        # Leer hoja de Trades
        df = pd.read_excel(archivo, sheet_name='Trades')
        
        # --- LA SOLUCIÓN AL KEYERROR ---
        # 1. Quitar espacios invisibles al principio o final de los títulos
        df.columns = df.columns.str.strip()
        
        # 2. Buscar dinámicamente si está en inglés o en español
        if 'Cumulative PnL USDT' in df.columns:
            col_pyg = 'Cumulative PnL USDT'
        elif 'PyG acumuladas USDT' in df.columns:
            col_pyg = 'PyG acumuladas USDT'
        else:
            # Si TradingView cambió el nombre de nuevo, la terminal te dirá cuáles son los nombres reales
            print(f"⚠️ ¡Atención! No encontré la columna en {codigo}. Las columnas reales son: {df.columns.tolist()}")
            continue
        
        # Filtrar solo las salidas
        df = df[df['Tipo'].astype(str).str.contains('Salida', case=False, na=False)].copy()
        df['Fecha'] = pd.to_datetime(df['Fecha y hora'])
        
        # Matemática del Drawdown
        df['Equity'] = capital_inicial + pd.to_numeric(df[col_pyg], errors='coerce')
        df['Pico'] = df['Equity'].cummax()
        df['DD %'] = ((df['Equity'] / df['Pico']) - 1) * 100
        
        # Downsampling Semanal
        df.set_index('Fecha', inplace=True)
        df_semanal = df['DD %'].resample('W').min().dropna()
        
        # Formato JSON
        fechas_json = df_semanal.index.strftime('%b %y').tolist()
        drawdown_json = [round(float(val), 2) for val in df_semanal.values]
        
        # Exportar
        ruta_salida = os.path.join(carpeta_destino, f"{codigo}.json")
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump({
                "fechas": fechas_json,
                "drawdown": drawdown_json
            }, f)
            
    except Exception as e:
        print(f"❌ Error al procesar {archivo}: {e}")

print("\n¡PROCESO FINALIZADO! Revisa tu carpeta 'datos'.")