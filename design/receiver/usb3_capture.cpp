// Read-only USB3 connection capture using the installed Microsoft Windows SDK.
// Only GET_HUB_INFORMATION_EX, GET_NODE_CONNECTION_INFORMATION_EX and EX_V2
// are sent. No reset/cycle/configuration/descriptor-string requests are made.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <initguid.h>
#include <setupapi.h>
#include <usbioctl.h>
#include <usbiodef.h>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

static const char* speed(bool queryOk, ULONG flags) {
    if (!queryOk) return "unknown";
    if (flags & 4) return "SuperSpeedPlus_or_higher";
    if (flags & 1) return "SuperSpeed_or_higher";
    return "not_operating_at_SuperSpeed";
}
static std::string hex4(USHORT n) {
    std::ostringstream s;
    s << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << n;
    return s.str();
}
int main(int argc, char** argv) {
    if (argc==2 && std::string(argv[1])=="--self-test") {
        // Capability bits (1 and 3) must never be interpreted as active speed.
        bool ok=std::string(speed(true, 2|8))=="not_operating_at_SuperSpeed"
            && std::string(speed(true, 1|2))=="SuperSpeed_or_higher"
            && std::string(speed(true, 1|2|4|8))=="SuperSpeedPlus_or_higher"
            && std::string(speed(false, 15))=="unknown";
        std::cout << (ok ? "PASS speed classification\n" : "FAIL\n");
        return ok ? 0 : 1;
    }
    HDEVINFO devices=SetupDiGetClassDevsW(&GUID_DEVINTERFACE_USB_HUB,nullptr,nullptr,
                                         DIGCF_PRESENT|DIGCF_DEVICEINTERFACE);
    if (devices==INVALID_HANDLE_VALUE) {
        std::cerr << "SetupDiGetClassDevs error " << GetLastError() << '\n'; return 1;
    }
    std::vector<std::string> ssDevices, errors;
    unsigned hubs=0, ports=0, connected=0, nonSS=0, unknown=0;
    for (DWORD index=0;;index++) {
        SP_DEVICE_INTERFACE_DATA di{};di.cbSize=sizeof(di);
        if (!SetupDiEnumDeviceInterfaces(devices,nullptr,&GUID_DEVINTERFACE_USB_HUB,index,&di)) {
            if (GetLastError()!=ERROR_NO_MORE_ITEMS) errors.push_back("interface_enumeration_"+std::to_string(GetLastError()));
            break;
        }
        DWORD bytes=0;
        SetupDiGetDeviceInterfaceDetailW(devices,&di,nullptr,0,&bytes,nullptr);
        if (bytes<sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W)) {errors.push_back("interface_size");continue;}
        std::vector<BYTE> detailBytes(bytes);
        auto detail=reinterpret_cast<PSP_DEVICE_INTERFACE_DETAIL_DATA_W>(detailBytes.data());
        detail->cbSize=sizeof(*detail);
        if (!SetupDiGetDeviceInterfaceDetailW(devices,&di,detail,bytes,nullptr,nullptr)) {
            errors.push_back("interface_detail_"+std::to_string(GetLastError()));continue;
        }
        // Zero requested data access: all three IOCTLs use FILE_ANY_ACCESS.
        HANDLE hub=CreateFileW(detail->DevicePath,0,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,
                              OPEN_EXISTING,0,nullptr);
        if (hub==INVALID_HANDLE_VALUE) {errors.push_back("hub_open_"+std::to_string(GetLastError()));continue;}
        USB_HUB_INFORMATION_EX hi{};DWORD received=0;
        if (!DeviceIoControl(hub,IOCTL_USB_GET_HUB_INFORMATION_EX,&hi,sizeof(hi),&hi,sizeof(hi),&received,nullptr)) {
            errors.push_back("hub_information_"+std::to_string(GetLastError()));CloseHandle(hub);continue;
        }
        ++hubs;
        for (ULONG port=1;port<=hi.HighestPortNumber;port++) {
            ++ports;
            // Space for the variable pipe-list tail, using SDK layouts/packing.
            std::vector<BYTE> infoBytes(sizeof(USB_NODE_CONNECTION_INFORMATION_EX)+32*sizeof(USB_PIPE_INFO));
            auto info=reinterpret_cast<PUSB_NODE_CONNECTION_INFORMATION_EX>(infoBytes.data());
            info->ConnectionIndex=port;
            if (!DeviceIoControl(hub,IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX,
                                 info,DWORD(infoBytes.size()),info,DWORD(infoBytes.size()),&received,nullptr)) {
                errors.push_back("port_information_"+std::to_string(GetLastError()));continue;
            }
            if (info->ConnectionStatus==NoDeviceConnected) continue;
            if (info->ConnectionStatus!=DeviceConnected) {
                errors.push_back("port_connection_status_"+std::to_string(info->ConnectionStatus));continue;
            }
            ++connected;
            USB_NODE_CONNECTION_INFORMATION_EX_V2 v2{};
            v2.ConnectionIndex=port;v2.Length=sizeof(v2);
            v2.SupportedUsbProtocols.Usb300=1;
            bool ok=DeviceIoControl(hub,IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX_V2,
                                   &v2,sizeof(v2),&v2,sizeof(v2),&received,nullptr)!=FALSE;
            if (!ok) {++unknown;errors.push_back("port_speed_v2_"+std::to_string(GetLastError()));continue;}
            if (!(v2.Flags.ul & (1|4))) {++nonSS;continue;}
            std::ostringstream row;
            row << "{\"hub_index_in_this_capture\":" << index << ",\"port\":" << port
                << ",\"vid\":\"" << hex4(info->DeviceDescriptor.idVendor)
                << "\",\"pid\":\"" << hex4(info->DeviceDescriptor.idProduct)
                << "\",\"bcdDevice\":\"" << hex4(info->DeviceDescriptor.bcdDevice)
                << "\",\"bcdUSB\":\"" << hex4(info->DeviceDescriptor.bcdUSB)
                << "\",\"is_hub\":" << (info->DeviceIsHub ? "true" : "false")
                << ",\"operating_speed\":\"" << speed(ok,v2.Flags.ul)
                << "\",\"speed_flags_raw\":" << v2.Flags.ul
                << ",\"port_supports_usb3\":" << (v2.SupportedUsbProtocols.Usb300 ? "true" : "false") << "}";
            ssDevices.push_back(row.str());
        }
        CloseHandle(hub);
    }
    SetupDiDestroyDeviceInfoList(devices);
    std::cout << "{\"schema_version\":1,\"scope\":\"Read-only current USB3 connection metadata; no throughput or optical-path proof\","
              << "\"hub_interfaces_queried\":" << hubs << ",\"ports_queried\":" << ports
              << ",\"connected_devices_seen\":" << connected
              << ",\"non_superspeed_devices_omitted\":" << nonSS
              << ",\"unknown_speed_devices\":" << unknown << ",\"usb3_connections\":[";
    for (size_t i=0;i<ssDevices.size();i++) std::cout << (i ? "," : "") << ssDevices[i];
    std::cout << "],\"errors\":[";
    for (size_t i=0;i<errors.size();i++) std::cout << (i ? "," : "") << '"' << errors[i] << '"';
    std::cout << "]}\n";
    return errors.empty() ? 0 : 2;
}
