plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "in.kitchcu.shell"
    compileSdk = 34
    defaultConfig {
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }
    flavorDimensions += "persona"
    productFlavors {
        create("customer") {
            dimension = "persona"
            applicationId = "in.kitchcu.customer"
            resValue("string", "app_name", "kitchCU - customers")
            buildConfigField("String", "LAUNCH_URL", "\"https://customer.kitchcu.com/\"")
            buildConfigField("String", "DEBUG_LAUNCH_URL", "\"http://10.0.2.2:13001/\"")
        }
        create("kitchen") {
            dimension = "persona"
            applicationId = "in.kitchcu.kitchen"
            resValue("string", "app_name", "kitchCU - kitchen owner")
            buildConfigField("String", "LAUNCH_URL", "\"https://kitchen.kitchcu.com/\"")
            buildConfigField("String", "DEBUG_LAUNCH_URL", "\"http://10.0.2.2:13002/\"")
        }
        create("admin") {
            dimension = "persona"
            applicationId = "in.kitchcu.admin"
            resValue("string", "app_name", "kitchCU - admin")
            buildConfigField("String", "LAUNCH_URL", "\"https://admin.kitchcu.com/\"")
            buildConfigField("String", "DEBUG_LAUNCH_URL", "\"http://10.0.2.2:13003/\"")
        }
    }
    buildTypes {
        getByName("debug") {
            buildConfigField("Boolean", "USE_DEBUG_HOST", "true")
        }
        getByName("release") {
            isMinifyEnabled = false
            buildConfigField("Boolean", "USE_DEBUG_HOST", "false")
        }
    }
    buildFeatures {
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
}
