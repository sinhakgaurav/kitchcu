import UIKit
import WebKit

final class WebShellViewController: UIViewController, WKNavigationDelegate {
    private var webView: WKWebView!

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.04, green: 0.11, blue: 0.20, alpha: 1)
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.navigationDelegate = self
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        view.addSubview(webView)
        webView.load(URLRequest(url: Self.launchURL()))
    }

    private static func launchURL() -> URL {
        #if DEBUG
        if let debug = Bundle.main.object(forInfoDictionaryKey: "CKACDebugLaunchURL") as? String,
           let url = URL(string: debug) {
            return url
        }
        #endif
        let raw = Bundle.main.object(forInfoDictionaryKey: "CKACLaunchURL") as? String
            ?? "https://customer.kitchcu.com/"
        return URL(string: raw)!
    }
}
