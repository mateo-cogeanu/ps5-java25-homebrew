/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host layout preview ONLY. Synthetic JNI calls below are not JVM evidence.
 */
#include "jni.h"
using Initializer=void (*)();
extern "C" {
Initializer __jvm_init_array_start[1]{};
Initializer __jvm_init_array_end[1]{};
jint JNI_GetDefaultJavaVMInitArgs(void *) {return JNI_OK;}
jint JNI_GetCreatedJavaVMs(JavaVM **,jsize,jsize *count) {*count=0;return JNI_OK;}
jint JNI_CreateJavaVM(JavaVM **,void **,void *) {return JNI_ERR;}
}
