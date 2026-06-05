# 🌊 MAC Flooding — Desbordamiento de la Tabla CAM

## 🎯 Objetivo del Laboratorio

Demostrar cómo un atacante puede desbordar la tabla CAM (*Content Addressable Memory*) de un switch Cisco inyectando masivamente frames con MACs origen aleatorias, forzando al switch a comportarse como un hub y retransmitir el tráfico unicast por todos los puertos, permitiendo la captura de tráfico ajeno.

---

## 📋 Objetivo del Script

El script `MAC_Flooding.py` genera frames Ethernet con MACs origen y destino aleatorias (unicast), los encapsula en `Dot1Q` con VLAN 10 y los envía a través de `ens4` a máxima velocidad usando un socket L2 persistente. Cada frame con una MAC origen nueva es aprendida por el switch en su tabla CAM hasta agotarla.

### Parámetros usados

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `INTERFACE` | `ens4` | Interfaz física de Kali (trunk hacia SW-1) |
| `VLAN_ID` | `10` | VLAN objetivo para saturar |
| `PAQUETES` | `15000` | Número de frames a inyectar |
| `INTERVALO` | `0.0005 s` | Retardo entre frames (~2000 pkt/s) |
| `PAYLOAD` | `b"X" * 64` | Relleno del frame |

### Requisitos para utilizar la herramienta

```bash
# Dependencias
pip install scapy

# No requiere IP forwarding

# Ejecución
sudo python3 MAC_Flooding.py
```

---

## 🔧 Documentación del Funcionamiento del Script

### Flujo de ejecución

```
1. Abrir socket L2 persistente (conf.L2socket)
2. Para cada frame (1 a 15000):
     a. Generar MAC origen aleatoria unicast:
          octetos[0] &= 0xFE   ← garantiza bit unicast
     b. Generar MAC destino aleatoria
     c. Construir frame:
          Ether(src=MAC_src, dst=MAC_dst) /
          Dot1Q(vlan=10) /
          b"X" * 64
     d. sock.send(frame)  ← sin overhead por paquete
     e. Cada 1000 frames → imprimir estadísticas
3. Ctrl+C → mostrar frames y MACs únicas enviadas
```

### Por qué la MAC origen debe ser unicast

El switch **solo aprende** MACs unicast en su tabla CAM. Si el bit 0 del primer octeto es `1`, la dirección es multicast/broadcast y el switch la ignora para el aprendizaje. Por eso el script aplica:

```python
octetos[0] &= 0xFE   # fuerza bit 0 = 0 → unicast
```

### Comportamiento del switch antes y después

```
ANTES (tabla CAM normal):
  Puerto Et0/1 → MAC-A (VPC-1)
  Puerto Et0/2 → MAC-B (VPC-2)
  Tráfico VPC-1 → VPC-2: frame enviado SOLO por Et0/2

DESPUÉS (tabla CAM desbordada):
  Tabla llena de MACs falsas
  MACs reales → desplazadas / no encontradas
  Tráfico VPC-1 → VPC-2: frame replicado por TODOS los puertos
  Kali (Et0/3) → recibe tráfico que no le corresponde
```

### Captura de tráfico ajeno durante el ataque

```bash
# En Kali, mientras corre el MAC Flooding:
sudo tcpdump -i ens4.10 -n not arp
# → captura tráfico unicast entre VPCs que normalmente
#   no llegaría a Kali
```

---

## 🗺️ Documentación de la Red

### Topología

```
        [ R1 — IOU L3 ]
               |
           e0/0 (trunk)
               |
        [ SW-1 — IOL L2 ]  ← tabla CAM objetivo
         e0/1       e0/2       e0/3
          |           |           |
       [SW-3]       [SW-2]   [Kali]
       VPC-1,4      VPC-2,3   ens4 (física)
       VLAN 10      VLAN 20   192.168.10.50
```

### Tabla CAM de referencia (Cisco IOL L2)

| Parámetro | Valor típico |
|-----------|--------------|
| Capacidad máxima tabla CAM | ~8.192 entradas |
| Aging time por defecto | 300 segundos |
| Entradas para desbordar | ~8.000 MACs únicas |
| Tiempo del ataque | ~4 segundos a 2000 pkt/s |

---

## 📸 Capturas de Pantalla

> Insertar capturas en esta sección:

1. **`img/01_cam_antes.png`** — `show mac-address-table count` en SW-1 antes del ataque. Pocas entradas dinámicas.
2. **`img/02_script_corriendo.png`** — Terminal Kali con el script mostrando el contador de frames y tasa (pkt/s).
3. **`img/03_cam_saturada.png`** — `show mac-address-table count` durante el ataque. Entradas dinámicas en máximo.
4. **`img/04_tcpdump_captura.png`** — `tcpdump` en Kali capturando tráfico unicast ajeno (entre VPCs).

---

## 🛡️ Contra-medidas

### Port Security

```
! Limitar MACs aprendidas por puerto de acceso
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# switchport port-security
SW-1(config-if)# switchport port-security maximum 3
SW-1(config-if)# switchport port-security violation restrict
! (restrict: descarta frames con MAC desconocida, no apaga el puerto)

! Alternativa más estricta:
SW-1(config-if)# switchport port-security violation shutdown
! (shutdown: apaga el puerto automáticamente al detectar violación)

! Verificación
SW-1# show port-security
SW-1# show port-security interface Ethernet0/3
SW-1# show mac-address-table
```

### Reducir el aging time

```
! Entradas antiguas expiran más rápido, liberando espacio
SW-1(config)# mac-address-table aging-time 60
```

> **Efecto:** Con Port Security `maximum 3`, el switch solo aprende 3 MACs por puerto. Los frames con MACs nuevas son descartados (`restrict`) o el puerto se cierra (`shutdown`). El MAC Flooding queda completamente neutralizado.
