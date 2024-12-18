import time
import ujson
from umqtt.simple import MQTTClient
import network
import random
import dht
from machine import Pin, I2C, SoftI2C,ADC
from time import sleep
#import BME280
#from bmp280 import BMP280

# ESP32 - Pin assignment
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
sensor = dht.DHT11(Pin(23))
chuva = ADC(Pin(36)) # sensor detector de chuva 36 atslands
solo = ADC(Pin(37)) # sensor de humidade solo  37 atslands
chuva.atten(ADC.ATTN_11DB)
solo.atten(ADC.ATTN_11DB)

def gerar_numero_aleatorio():
    return random.randint(20, 50)

# Configurações de provisionamento e MQTT
provision_device_key = "kdd0uh850p5i3ex5h5o4"
provision_device_secret = "ox3d0qb9i6hbje3m21c2"
THINGSBOARD_HOST = "mqtt.thingsboard.cloud"
THINGSBOARD_PORT = 1883
PROVISION_REQUEST_TOPIC = "/provision/request"
PROVISION_RESPONSE_TOPIC = "/provision/response"

# Funções auxiliares para lidar com credenciais
def save_credentials(credentials):
    with open("credentials.json", "w") as file:
        file.write(ujson.dumps(credentials))

def load_credentials():
    try:
        with open("credentials.json", "r") as file:
            return ujson.loads(file.read())
    except Exception as e:
        print(f"Erro ao carregar credenciais: {e}")
        return None

def clean_credentials():
    with open("credentials.json", "w") as file:
        file.write("")
        
def internet_connect():
    print("Conectando-se ao Wi-Fi", end="")
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect("Redmi Note 11S", "minhasenha123")
    while not sta_if.isconnected():
      print(".", end="")
      time.sleep(0.1)
    print(" Conectado!")

# Função de provisionamento
def provision_device():
    print("[Provisioning] Iniciando provisionamento...")
    client = MQTTClient(
        "provision_client", THINGSBOARD_HOST, port=THINGSBOARD_PORT, user="provision", password=""
    )
    try:
        client.connect()
        print("[Provisioning] Conectado ao ThingsBoard.")
        provision_request = ujson.dumps({
            "deviceName": "nome2",
            "provisionDeviceKey": provision_device_key,
            "provisionDeviceSecret": provision_device_secret
        })
        client.publish(PROVISION_REQUEST_TOPIC, provision_request)
        print(f"[Provisioning] Requisição enviada: {provision_request}")
        
        # Aguarda a resposta de provisionamento
        def on_message(topic, msg):
            print(f"[Provisioning] Resposta recebida: {msg}")
            decoded_message = ujson.loads(msg)
            if decoded_message.get("status") == "SUCCESS":
                save_credentials(decoded_message["credentialsValue"])
                print("[Provisioning] Credenciais salvas com sucesso.")
            else:
                print(f"[Provisioning] Erro: {decoded_message.get('errorMsg')}")
            client.disconnect()

        
        client.set_callback(on_message)
       
        client.subscribe(PROVISION_RESPONSE_TOPIC)
        
        client.wait_msg()  # Aguarda a mensagem de resposta
        
    except Exception as e:
        print(f"[Provisioning] Erro: {e}")

    
# Publicação de dados com o cliente MQTT provisionado
def publish_telemetry():
    credentials = load_credentials()
    if not credentials:
        print("[Telemetry] Nenhuma credencial encontrada. Execute o provisionamento primeiro.")
        return

    print("[Telemetry] Iniciando publicação de telemetria...")
    client = MQTTClient("telemetry_client", THINGSBOARD_HOST, port=THINGSBOARD_PORT, user=credentials, password="")
    try:
        client.connect()
        print("[Telemetry] Conectado ao ThingsBoard.")
        while True:
            #xsensor.measure()
            
            try:
                chuva_valor = chuva.read()
                if chuva_valor is None:
                    chuva_valor = 4095  # Valor default em caso de leitura inválida
            except:
                chuva_valor = 4095  # Valor default se ocorrer erro na leitura

            try:
                solo_valor = solo.read()
                if solo_valor is None:
                    solo_valor = 4095  # Valor default em caso de leitura inválida
            except:
                solo_valor = 4095  # Valor default se ocorrer erro na leitura

            payload = ujson.dumps(
                    {
                    "temperature_dht11": 60,
                    "humidity_dht11": 60,
                    "detector_chuva": chuva_valor,
                    "umidade_solo":  solo_valor
                    }
            )

            client.publish("v1/devices/me/telemetry", payload)
            print(f"[Telemetry] Publicado: {payload}")
            time.sleep(5)
    except Exception as e:
        print(f"[Telemetry] Erro: {e}")
        print("Gerando novas credenciais")
        clean_credentials()
        provision_device()
        publish_telemetry()
    finally:
        client.disconnect()

def scan_i2c_bus():
    devices = i2c.scan()
    if devices:
        print("Dispositivos I2C encontrados:", [hex(device) for device in devices])
    else:
        print("Nenhum dispositivo I2C encontrado.")

if __name__ == "__main__":
    i =0
   # while True:
    #  chuva_valor = chuva.read()
     # solo_valor = solo.read()
      #print(chuva_valor)
      #print("\n")
      #print(solo_valor)
      #sleep(3)
      #print(i)
      #i=i+1
    internet_connect()
    credentials = load_credentials()
    print(credentials)
    if not credentials:
        provision_device()  # Executa o provisionamento
    publish_telemetry()  # Publica dados de telemetria
