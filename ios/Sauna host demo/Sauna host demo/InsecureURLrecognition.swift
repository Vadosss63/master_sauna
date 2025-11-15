//
//  InsecureURLrecognition.swift
//  Sauna host demo
//
//  Created by Timur Lavrukhin on 15.11.2025.
//

import Foundation

final class InsecureURLSessionDelegate: NSObject, URLSessionDelegate {
    static let shared = InsecureURLSessionDelegate()

    private override init() {
        super.init()
    }

    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {

        // Если это проверка сервера (SSL/TLS)
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let serverTrust = challenge.protectionSpace.serverTrust {
            let credential = URLCredential(trust: serverTrust)
            completionHandler(.useCredential, credential)   // 👈 принимаем ЛЮБОЙ сертификат
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }
}
