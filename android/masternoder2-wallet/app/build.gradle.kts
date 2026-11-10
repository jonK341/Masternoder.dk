plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "dk.masternoder.wallet"
    compileSdk = 35

    defaultConfig {
        applicationId = "dk.masternoder.wallet"
        minSdk = 26
        targetSdk = 35
        versionCode = 9265
        versionName = "9.2.6.5"
        // Live site URL is injected at build time (WALLET_URL / -Pmn2.walletUrl).
        // Default is loopback so the repo never hardcodes the public site host.
        buildConfigField(
            "String",
            "WALLET_URL",
            "\"${project.findProperty("mn2.walletUrl") ?: "https://127.0.0.1/wallets"}\"",
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        debug {
            applicationIdSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.webkit:webkit:1.12.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
}
