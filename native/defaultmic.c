// Print the name of the current default input device (e.g. "MacBook Air Microphone").
#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
int main(void) {
    AudioObjectPropertyAddress a = {kAudioHardwarePropertyDefaultInputDevice,
                                    kAudioObjectPropertyScopeGlobal, kAudioObjectPropertyElementMain};
    AudioDeviceID dev = 0; UInt32 s = sizeof dev;
    if (AudioObjectGetPropertyData(kAudioObjectSystemObject, &a, 0, NULL, &s, &dev) || !dev) return 1;
    a.mSelector = kAudioObjectPropertyName;
    CFStringRef name = NULL; s = sizeof name;
    if (AudioObjectGetPropertyData(dev, &a, 0, NULL, &s, &name) || !name) return 1;
    char buf[256]; CFStringGetCString(name, buf, sizeof buf, kCFStringEncodingUTF8);
    CFRelease(name); printf("%s\n", buf); return 0;
}
