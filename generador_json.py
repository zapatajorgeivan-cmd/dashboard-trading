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
        
        # 1. Leer el archivo Excel sin cargar una hoja específica todavía para ver qué hojas tiene
        xls = pd.ExcelFile(archivo)
        hojas_disponibles = xls.sheet_names
        
        # 2. Buscar la hoja correcta, ya sea 'Trades' u 'Operaciones'
        hoja_objetivo = None
        for posible_nombre in ['Trades', 'Operaciones']:
            if posible_nombre in hojas_disponibles:
                hoja_objetivo = posible_nombre
                break
                
        if hoja_objetivo is None:
            print(f"Advertencia: No se encontró la hoja de trades en {nombre_base}. Saltando...")
            continue # Salta al siguiente archivo si no encuentra ninguna de las dos hojas
            
        # 3. Leer la hoja encontrada
        df = pd.read_excel(xls, sheet_name=hoja_objetivo)
        df.columns = df.columns.str.strip()
        
        # 4. Diccionario para traducir/estandarizar columnas al formato original
        # Si encuentra las claves (izquierda), las renombra a los valores (derecha)
        mapeo_columnas = {
            'PyG netas USDT': 'Net PnL USDT',
            'Rentabilidad %': 'Net PnL %',
            'PyG acumuladas USDT': 'Cumulative PnL USDT',
            'PyG acumuladas %': 'Cumulative PnL %',
            # Puedes agregar más aquí en el futuro si cambian otros nombres
        }
        
        # Renombrar las columnas usando el diccionario
         
        df = df.rename(columns=mapeo_columnas)
        
        df = df[df['Tipo'].astype(str).str.contains('Salida', case=False, na=False)].copy()
        
        # --- SOLUCIÓN DEL AÑO 70 (Lector inteligente de Excel) ---
        df['Fecha'] = pd.to_datetime(df['Fecha y hora'], errors='coerce')
        
        # Si la fecha cayó en 1970, significa que Excel mandó un número de serie. Lo corregimos:
        if df['Fecha'].dt.year.min() == 1970:
            df['Fecha'] = pd.to_datetime(df['Fecha y hora'], unit='D', origin='1899-12-30', errors='coerce')
            
        df = df.dropna(subset=['Fecha']) # Eliminar filas sin fecha
        
        # Cálculos de Capital
        df['Equity'] = capital_inicial + pd.to_numeric(df['Cumulative PnL USDT'], errors='coerce')
        df['Pico'] = df['Equity'].cummax()
        df['DD %'] = ((df['Equity'] / df['Pico']) - 1) * 100
        
        # --- CONVERSIÓN UNIX SEGURA ---
        df['UNIX'] = df['Fecha'].apply(lambda x: int(x.timestamp()))
        df = df.sort_values('UNIX', ascending=True)
        df = df.drop_duplicates(subset=['UNIX'], keep='last')
        
        # Métricas
        rent_media = df['Net PnL %'].mean()
        std_dev = df['Net PnL %'].std()
        sharpe = (rent_media / std_dev) if std_dev != 0 else 0
        
        g_bruta = df[df['Net PnL USDT'] > 0]['Net PnL USDT'].sum()
        p_bruta = abs(df[df['Net PnL USDT'] < 0]['Net PnL USDT'].sum())
        p_factor = g_bruta / p_bruta if p_bruta != 0 else g_bruta
        mdd = abs(df['DD %'].min())
        calmar = (rent_media * 52) / mdd if mdd != 0 else 0
        
        # Exportación a formato TradingView
        equity_data = [{"time": int(t), "value": round(float(v), 2)} for t, v in zip(df['UNIX'], df['Equity'])]
        drawdown_data = [{"time": int(t), "value": round(float(v), 2)} for t, v in zip(df['UNIX'], df['DD %'])]
        
        if len(equity_data) > 0:
            tiempo_inicio = equity_data[0]["time"] - 1
            equity_data.insert(0, {"time": tiempo_inicio, "value": capital_inicial})
            drawdown_data.insert(0, {"time": tiempo_inicio, "value": 0.0})

        data = {
            "equity_data": equity_data,
            "drawdown_data": drawdown_data,
            "metricas": {"sharpe": round(sharpe, 2), "profit_factor": round(p_factor, 2), "calmar": round(calmar, 2)}
        }
        
        with open(os.path.join(carpeta_destino, f"{codigo}.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
    except Exception as e:
        print(f"Error en {codigo}: {e}")

print("¡PROCESO FINALIZADO!")
