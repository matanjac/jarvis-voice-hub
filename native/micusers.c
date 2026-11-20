// List processes currently capturing audio input (macOS 14.2+ CoreAudio process objects).
//   micusers                 -> prints "pid bundle-id" per process using the mic
//   micusers --others PID    -> exit 0 if any process other than PID uses the mic, else 1
#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static OSStatus get(AudioObjectID obj, AudioObjectPropertySelector sel, UInt32 *size, void *out) {
    AudioObjectPropertyAddress a = {sel, kAudioObjectPropertyScopeGlobal,
                                    kAudioObjectPropertyElementMain};
    return AudioObjectGetPropertyData(obj, &a, 0, NULL, size, out);
}

int main(int argc, char **argv) {
    pid_t exclude = (argc > 2 && strcmp(argv[1], "--others") == 0) ? atoi(argv[2]) : -1;
    AudioObjectPropertyAddress a = {kAudioHardwarePropertyProcessObjectList,
                                    kAudioObjectPropertyScopeGlobal,
                                    kAudioObjectPropertyElementMain};
    UInt32 size = 0;
    if (AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, &a, 0, NULL, &size)) return 2;
    UInt32 n = size / sizeof(AudioObjectID);
    AudioObjectID *ids = malloc(size);
    if (AudioObjectGetPropertyData(kAudioObjectSystemObject, &a, 0, NULL, &size, ids)) return 2;
    int found = 0;
    for (UInt32 i = 0; i < n; i++) {
        UInt32 running = 0, s = sizeof(running);
        if (get(ids[i], kAudioProcessPropertyIsRunningInput, &s, &running) || !running) continue;
        pid_t pid = -1; s = sizeof(pid);
        get(ids[i], kAudioProcessPropertyPID, &s, &pid);
        if (pid == exclude) continue;
        found = 1;
        if (exclude < 0) {
            CFStringRef b = NULL; s = sizeof(b);
            char buf[256] = "?";
            if (!get(ids[i], kAudioProcessPropertyBundleID, &s, &b) && b) {
                CFStringGetCString(b, buf, sizeof buf, kCFStringEncodingUTF8);
                CFRelease(b);
            }
            printf("%d %s\n", pid, buf);
        }
    }
    free(ids);
    return found ? 0 : 1;
}
