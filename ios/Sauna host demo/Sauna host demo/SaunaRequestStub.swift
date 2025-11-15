//
//  SaunaRequestStub.swift
//  Sauna host demo
//
//  Created by Timur Lavrukhin on 15.11.2025.
//

import Foundation

struct TextGenerationAPIClientStub {
    // Замените URL на ваш реальный endpoint
    func generateText(from userText: String) async throws -> String {
        sleep(5)
        return "User said" + userText
    }
}
