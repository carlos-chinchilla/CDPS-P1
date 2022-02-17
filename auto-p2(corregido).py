#12/12/2021 20:41
#! /usr/bin/python
#! /usr/bin/sudo
# coding=utf-8

import sys
import json
from subprocess import call, run
from lxml import etree

#La orden va a ser el segundo argumento del comando ya que el primero será el nombre del script
orden = str(sys.argv[1])

#Definicion de la primera orden (prepare)
def prepare():

    #Si no se ha introducido un segundo parámentro, se arrancan 3 servidores
    if len(sys.argv)==2:
        numero_servidores=3
        servidores={"num_serv":numero_servidores}
    
    #Si se ha introducido parámetro, se arranca ese numero de servidores
    elif int(sys.argv[2])>=1 and int(sys.argv[2])<=5:
        numero_servidores=int(sys.argv[2])
        servidores={"num_serv":numero_servidores}

    else:
        print("Error, the number of servers can´t be more than 5")
        sys.exit

    #Guardamos el valor del numero de servidores en el archivo auto-p2.json
    with open("servidores.json", "w") as f:
        json.dump(servidores, f)

     #Creamos un directorio para almacenar todas las configuraciones de las MVs 
    call(["mkdir /mnt/tmp/archivos-configuracion"], shell=True)
    call(["cp servidores.json /mnt/tmp/archivos-configuracion/auto-p2.json"], shell=True)

    print("Creamos las imagenes de c1, lb y los servidores")
    print()

     #Creamos los ficheros COW y lo metemos en archivos-configuración
     #De c1
    call(["qemu-img create -f qcow2 -b cdps-vm-base-pc1.qcow2 c1.qcow2"], shell=True)
     #De lb
    call(["qemu-img create -f qcow2 -b cdps-vm-base-pc1.qcow2 lb.qcow2"], shell=True)
     #De los servidores. Usamos un contador
    
    i0=1
    while i0<=numero_servidores:
        call(["qemu-img create -f qcow2 -b cdps-vm-base-pc1.qcow2 s"+ str(i0) +".qcow2"], shell=True)
        i0=i0+1
    
        
    print("Modificamos la platilla XML para c1, lb y los servidores")
    print()
    #Modificamos los ficheros XML
    #De c1
    tree=etree.parse("plantilla-vm-pc1.xml")
    fichero1=tree.getroot()
        #Cambiamos nombre
    nombre=fichero1.find("name")
    nombre.text="c1"
        #Cambiamos direccion
    direccion=fichero1.find("./devices/disk/source")
    direccion.set("file", "/mnt/tmp/archivos-configuracion/c1.qcow2")
        #Cambiamos interfaz
    interfaz=fichero1.find("./devices/interface/source")
    interfaz.set("bridge", "LAN1")
        #Sobreescribimos el archivo
    tree.write("/mnt/tmp/archivos-configuracion/c1.xml")

    #De lb
    tree1=etree.parse("plantilla-vm-pc1.xml")
    fichero2=tree1.getroot()
        #Cambiamos nombre
    nombre1=fichero2.find("name")
    nombre1.text="lb"
        #Cambiamos direccion
    direccion1=fichero2.find("./devices/disk/source")
    direccion1.set("file", "/mnt/tmp/archivos-configuracion/lb.qcow2")
        #Cambiamos interfaz
    interfaz1=fichero2.find("./devices/interface/source")
    interfaz1.set("bridge", "LAN1")
        #Añadimos nueva interfaz para lb
    parent=fichero2.find("./devices")
    interfaz2=etree.SubElement(parent, "interface")
    source=etree.SubElement(interfaz2,"source")
    model=etree.SubElement(interfaz2,"model")
    interfaz2.set("type","bridge")
    source.set("bridge","LAN2")
    model.set("type","virtio")
        #Sobreescribimos el archivo
    tree1.write("/mnt/tmp/archivos-configuracion/lb.xml")

    #De los servidores
    i=1
    while i<=numero_servidores:
        tree2=etree.parse("plantilla-vm-pc1.xml")
        fichero3=tree2.getroot()
        #Nombre
        nombre2=fichero3.find("name")
        nombre2.text="s"+str(i)
        #Direccion
        direccion2=fichero3.find("./devices/disk/source")
        direccion2.set("file", "/mnt/tmp/archivos-configuracion/s"+str(i)+".qcow2")
        #Interfaz
        interfaz3=fichero3.find("./devices/interface/source")
        interfaz3.set("bridge", "LAN2")
        tree2.write("/mnt/tmp/archivos-configuracion/s"+str(i)+".xml")
        i=i+1

    print("Creamos los bridges de las LAN")
    print()
    #Creamos los bridges correspondientes a las redes virtuales y la configuracion de red del host
    #call(["sudo ifconfig LAN1 10.0.1.3/24"], shell=True)
    #call(["sudo ip route add 10.0.0.0/16 via 10.0.1.1"], shell=True)

    call(["sudo brctl addbr LAN1"], shell=True)
    call(["sudo brctl addbr LAN2"], shell=True)
    call(["sudo ifconfig LAN1 up"], shell=True)
    call(["sudo ifconfig LAN2 up"], shell=True)

    #Configuracion lb como router
    print("Configuramos lb como router")
    print()
    call(["\
                sudo virt-edit -a lb.qcow2 /etc/sysctl.conf \
               -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' \
            "], shell = True)
    
    #Creamos los ficheros hostname y los metemos en las MVs
    print("Creamos los archivos hostname y los copiamos en las imagenes de las MVs")
    print()

    call(["echo c1 > hostname"], shell=True)
    call(["sudo virt-copy-in -a c1.qcow2 hostname /etc"], shell=True)


    call(["echo lb > hostname"], shell=True)
    call(["sudo virt-copy-in -a lb.qcow2 hostname /etc"], shell=True)


    i1=1
    while i<=numero_servidores:
        call(["echo s"+str(i1)+" > hostname"], shell=True)
        call(["sudo virt-copy-in -a s"+str(i1)+".qcow2 hostname /etc"], shell=True)

        i1=i1+1

    call(["rm hostname"], shell=True)

    #Creamos los ficheros interfaces y los metemos en las MVs
    print("Creamos los archivos interfaces y los copiamos en las MVs")
    print()

    interfazc1=open("interfaces","w")
    interfazc1.write("auto lo\niface lo inet loopback\nauto eth0\niface eth0 inet static\n    address 10.0.1.2\n    netmask 255.255.255.0\n    gateway 10.0.1.1\n    dns-nameservers 10.0.1.1")
    interfazc1.close()

    call(["sudo virt-copy-in -a c1.qcow2 interfaces /etc/network"], shell=True)
    call(["cp c1.qcow2 /mnt/tmp/archivos-configuracion"], shell=True)
    call(["rm interfaces"], shell=True)

    interfazlb=open("interfaces","w")
    interfazlb.write("auto lo\niface lo inet loopback\nauto eth0\niface eth0 inet static\n    address 10.0.1.1\n    netmask 255.255.255.0\nauto eth1\niface eth1 inet static\n    address 10.0.2.1\n    netmask 255.255.255.0")
    interfazlb.close()

    call(["sudo virt-copy-in -a lb.qcow2 interfaces /etc/network"],shell=True)
    call(["cp lb.qcow2 /mnt/tmp/archivos-configuracion"], shell=True)
    call(["rm interfaces"], shell=True)

    i2=1
    while i2<=numero_servidores:
        
        interfazservidores=open("interfaces","w")
        interfazservidores.write("auto lo\niface lo inet loopback\nauto eth0\niface eth0 inet static\n    address 10.0.2.1"+str(i2)+"\n    netmask 255.255.255.0\n    gateway 10.0.2.1\n    dns-nameservers 10.0.2.1")
        interfazservidores.close()

        call(["sudo virt-copy-in -a s"+str(i2)+".qcow2 interfaces /etc/network"], shell=True)
        call(["cp s"+str(i2)+".qcow2 /mnt/tmp/archivos-configuracion"], shell=True)
        call(["rm interfaces"], shell=True)
        i2=i2+1



def launch():
    with open("/mnt/tmp/archivos-configuracion/auto-p2.json","r") as read:
        datos=json.load(read)
        num_servidores=datos["num_serv"]
    
    print("El numero de servidores es "+str(num_servidores))
    print()

    #Vamos a proceder a arrancar las MVs y posteriormente a modificar sus archivos de configuracion para que funcionen correctamente
    call(["cp cdps-vm-base-pc1.qcow2 /mnt/tmp/archivos-configuracion"], shell=True)

    call(["sudo virsh define /mnt/tmp/archivos-configuracion/c1.xml"], shell=True)
    call(["sudo virsh define /mnt/tmp/archivos-configuracion/lb.xml"], shell=True)

    i2=1
    while i2<=num_servidores:
         call(["sudo virsh define /mnt/tmp/archivos-configuracion/s"+str(i2)+".xml"], shell=True)
         i2=i2+1

    call(["sudo virsh start c1"], shell=True)
    call(["xterm -e 'sudo virsh console c1' &"], shell=True)
    call(["sudo virsh start lb"], shell=True)
    call(["xterm -e 'sudo virsh console lb' &"], shell=True)

    i3=1
    while i3<=num_servidores:
         string=str(i3)
         call(["sudo virsh start s"+str(i3)], shell=True)
         call(["xterm -e 'sudo virsh console s%s' &" % str(i3)], shell=True)
         i3=i3+1

def launchx(servidor):

    call(["cp cdps-vm-base-pc1.qcow2 /mnt/tmp/archivos-configuracion"], shell=True)

    call(["sudo virsh define /mnt/tmp/archivos-configuracion/"+str(servidor)+".xml"], shell=True)
    call(["sudo virsh start "+str(servidor)], shell=True)
    call(["xterm -e 'sudo virsh console %s' &" % str(servidor)], shell=True)

def stop():

     #Obtenemos el numero de servidores a traves del archivo auto-p2.json
    with open("/mnt/tmp/archivos-configuracion/auto-p2.json","r") as read:
        datos=json.load(read)
        num_servidores=datos["num_serv"]

    call(["sudo virsh shutdown c1"], shell=True)
    call(["sudo virsh shutdown lb"], shell=True)

    i=1
    while i<=num_servidores:
         call(["sudo virsh shutdown s"+str(i)], shell=True)
         i=i+1

def stopx(MV):
    call(["sudo virsh shutdown "+str(MV)], shell=True)


def release():
    with open("/mnt/tmp/archivos-configuracion/auto-p2.json","r") as read:
        datos=json.load(read)
        num_servidores=datos["num_serv"]

    call(["sudo virsh destroy c1"], shell=True)
    call(["sudo virsh undefine c1"], shell=True)
    call(["sudo virsh destroy lb"], shell=True)
    call(["sudo virsh undefine lb"], shell=True)

    i=1
    while i<=num_servidores:
         call(["sudo virsh destroy s"+str(i)], shell=True)
         call(["sudo virsh undefine s"+str(i)], shell=True)
         i=i+1
    call(["sudo ifconfig LAN1 down"], shell = True)
    call(["sudo ifconfig LAN2 down"], shell = True)
    call(["sudo brctl delbr LAN1"], shell = True)
    call(["sudo brctl delbr LAN2"], shell = True)

    call(["rm c1.qcow2 lb.qcow2 servidores.json haproxy.cfg"], shell=True)
    call(["rm -Rf /mnt/tmp/archivos-configuracion"], shell=True)
    
    i1=1
    while i1<=num_servidores:
        call(["rm s"+str(i1)+".qcow2"], shell=True)
        i1=i1+1

def haproxy():
    with open("/mnt/tmp/archivos-configuracion/auto-p2.json","r") as read:
        datos=json.load(read)
        num_servidores=datos["num_serv"]
    
    call(["sudo virt-copy-out -a lb.qcow2 /etc/haproxy/haproxy.cfg ."], shell=True)
    call(["cp haproxy.cfg haproxy1.cfg"], shell=True)
    call(["rm -f haproxy.cfg"], shell=True)
    call(["mv haproxy1.cfg haproxy.cfg"], shell=True)

   

    cfghaproxy=open("haproxy.cfg","a")
    cfghaproxy.write("\n \
        frontend lb\n \
            bind  *:80\n \
            mode http\n \
            default_backend webservers \n \
        backend webservers\n \
            mode http\n \
            balance roundrobin\n ")
    cfghaproxy.close()

    i1=1
    while i1<=num_servidores:
        cfghaproxy=open("haproxy.cfg","a")
        cfghaproxy.write("\
            server s"+str(i1)+" 10.0.2.1"+str(i1)+":80 check\n ")
        cfghaproxy.close()
        i1=i1+1


    call(["sudo virt-copy-in -a lb.qcow2 haproxy.cfg /etc/haproxy"], shell=True)

    

if orden=="prepare":
    print("PREPARANDO ESCENARIO...")
    print()
    prepare()
    print()
    print("SE HAN CONFIGUIRADO TODAS LAS MAQUINAS VIRTUALES")
    print()

if orden=="launch":
    print("ARRANCANDO ESCENARIO...")
    print()
    launch()
    print()
    print("SE HAN ARRANCADO TODAS LAS MAQUINAS VIRTUALES")
    print()

if orden=="stop":
    print("PARANDO ESCENARIO...")
    print()
    stop()
    print()
    print("SE HAN PARADO TODAS LAS MAQUINAS VIRTUALES")
    print()

if orden=="release":
    print("LIBERANDO ESCENARIO...")
    print()
    release()
    print()
    print("SE HA LIBERADO TODO EL ESCENARIO")   
    print() 

if orden=="haproxy":
    print("CONFIGURANDO BALANCEADOR DE CARGA HAPROXY EN lb...")
    print()
    haproxy()
    print()
    print("HAproxy configurado")

if orden=="launchx":
    print("Se va a proceder a arrancar la MV: "+str(sys.argv[2]))
    print()
    launchx(servidor=sys.argv[2])
    print()
    print("Se ha arrancado la MV")
    print()

if orden=="stopx":
    print("Se va a proceder a parar "+str(sys.argv[2]))
    print()
    stopx(MV=sys.argv[2])
    print()
    print("Se ha parado la MV")
    print()
else:
    sys.exit

    