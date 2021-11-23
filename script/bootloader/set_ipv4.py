# usr/bin/env/python3

import depthai as dai
import re

def check_ipv4(ipv4):
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ipv4):
        raise Exception(f"Invalid IPv4 {ipv4}")
    return ipv4

def enter_new_config():
    print("\nNew IPv4 Configurations: ")
    ipv4 = check_ipv4(input("Enter IPv4: ").strip())
    mask = check_ipv4(input("Enter IPv4 Mask: ").strip())
    gateway = check_ipv4(input("Enter IPv4 Gateway: ").strip())
    is_static = True if input("Is this a static IPv4? (sets dynamic IPv4 if no) (y/n): ").strip() == "y" else False

    return ipv4, mask, gateway, is_static

def confirm_new_config(ipv4, mask, gateway, is_static):
    if is_static:
        print(f"\nWill flash static IPv4 {ipv4}, mask {mask}, gateway {gateway} to the POE device.")
        print("Note: Setting a static IPv4 won’t start DHCP client.")
    else:
        print(f"\nWill flash dynamic IPv4 {ipv4}, mask {mask}, gateway {gateway} to the POE device.")
        print("Note: Setting a dynamic IPv4 will set that IP as well as start DHCP client.")

    is_confirmed = True if input("\nConfirm flashing? (y/n): ").strip() == "y" else False

    if not is_confirmed:
        raise Exception("Flashing aborted.")

def run_config(info):
    with dai.DeviceBootloader(info) as bl:
        conf = dai.DeviceBootloader.Config()

        def see_config():
            print("\nCurrent IPv4 Configurations: ")
            print(f"IPv4:           {bl.readConfig().getIPv4()}")
            print(f"IPv4 Mask:      {bl.readConfig().getIPv4Mask()}") 
            print(f"IPv4 Gateway:   {bl.readConfig().getIPv4Gateway()}")
            print(f"Is IPv4 static: {bl.readConfig().isStaticIPV4()}")

        def perform_config(ipv4, mask, gateway, is_static):
            print("Flashing New Configurations...")
            
            if is_static:
                conf.setStaticIPv4(ipv4, mask, gateway)
            else:
                conf.setDynamicIPv4(ipv4, mask, gateway)
            
            (success, error) = bl.flashConfig(conf)

            if not success:
                print(f"Error occured while flashing the boot config: {error}")
            else:
                print(f"Boot config flashed successfully")

        see_config() # show current config
        ipv4, mask, gateway, is_static = enter_new_config()
        confirm_new_config(ipv4, mask, gateway, is_static)
        perform_config(ipv4, mask, gateway, is_static)
        see_config() # show new config

if __name__ == "__main__":
    ### current_ip = input("Enter IP of POE OAK Device: ").strip() # example: 172.16.15.17
    ### (found, info) = dai.DeviceBase.getDeviceByMxId(current_ip)
    (found, info) = dai.DeviceBootloader.getFirstAvailableDevice()

    if not found:
        raise Exception("No Device Found.")

    print(f"Found device with name: {info.desc.name}")
    run_config(info)