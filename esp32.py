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
chuva = ADC(Pin(34)) # sensor detector de chuva
solo = ADC(Pin(35)) # sensor de humidade solo
chuva.atten(ADC.ATTN_11DB)
solo.atten(ADC.ATTN_11DB)



def gerar_numero_aleatorio():
    return random.randint(20, 50)


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
# Configurações de provisionamento e MQTT
provision_device_key = "z9bvauzc8vbvozaojjx5"
provision_device_secret = "nbnnkvb61t70zjp3ib2e"
THINGSBOARD_HOST = "mqtt.thingsboard.cloud"
THINGSBOARD_PORT = 1883
PROVISION_REQUEST_TOPIC = "/provision/request"
PROVISION_RESPONSE_TOPIC = "/provision/response"

 
        
def internet_connect():
    print("Conectando-se ao Wi-Fi", end="")
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect("Redmi Note 11S", "minhasenha123")
    #sta_if.connect("LESC", "A33669608F")
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
            "deviceName": "estacao1",
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
            try:
                # Tenta medir os dados do sensor
                sensor.measure()
                temperatura = sensor.temperature()
                umidade = sensor.humidity()
            except Exception as e:
                # Trata qualquer erro que ocorra durante a leitura
                print(f"Erro ao medir com o sensor: {e}")
                temperatura = None
                umidade = None

            try:
                chuva_valor = chuva.read() if chuva else None
                solo_valor = solo.read() if solo else None
            except Exception as e:
                print(f"Erro ao ler valores de sensores: {e}")
                chuva_valor = None
                solo_valor = None

            payload = ujson.dumps(
                {
                    "temperature_dht11": temperatura,
                    "humidity_dht11": umidade,
                    "detector_chuva": chuva_valor,
                    "umidade_solo": solo_valor,
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
        credentials = load_credentials()
        print(credentials)
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
    
    internet_connect()
    credentials = load_credentials()
    print(credentials)
    if not credentials:
        provision_device()  # Executa o provisionamento
    publish_telemetry()  # Publica dados de telemetria
