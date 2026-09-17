package `in`.kitchcu.shell

import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.browser.customtabs.CustomTabsIntent
import androidx.browser.customtabs.TrustedWebUtils

class TwaActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val url = if (BuildConfig.USE_DEBUG_HOST) {
            BuildConfig.DEBUG_LAUNCH_URL
        } else {
            BuildConfig.LAUNCH_URL
        }
        val intent = CustomTabsIntent.Builder().build()
        TrustedWebUtils.launchAsTrustedWebActivity(this, intent, Uri.parse(url))
        finish()
    }
}
