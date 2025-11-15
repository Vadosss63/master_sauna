import Foundation

struct TextGenerationAPIClient {
    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        // 👇 важное место — свой URLSession с делегатом
        self.session = URLSession(configuration: config,
                                  delegate: InsecureURLSessionDelegate.shared,
                                  delegateQueue: nil)
    }

    struct RequestBody: Encodable {
        let message: String
    }

    struct ResponseBody: Decodable {
        let answer: String   // подстрой под свой JSON
    }

    func generateText(from userText: String) async throws -> String {
        guard let url = URL(string: "https://copypasta.fi:5001/process") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = RequestBody(message: userText)
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              200..<300 ~= httpResponse.statusCode else {
            throw URLError(.badServerResponse)
        }

        let decoded = try JSONDecoder().decode(ResponseBody.self, from: data)
        print(decoded.answer)
        return decoded.answer
    }
}
