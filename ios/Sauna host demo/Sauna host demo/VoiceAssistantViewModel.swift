//
//  VoiceAssistantViewModel.swift
//  Sauna host demo
//
//  Created by Timur Lavrukhin on 15.11.2025.
//

import Foundation
import Speech
import AVFoundation
import Combine

@MainActor
final class VoiceAssistantViewModel: NSObject, ObservableObject {
    // MARK: - Published state
    @Published var isRecording: Bool = false
    @Published var recognizedText: String = ""
    @Published var generatedText: String = ""
    @Published var errorMessage: String?
    @Published var isWaitingForResponse: Bool = false
    

    // MARK: - Speech recognition
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    // MARK: - Text-to-Speech
    private let speechSynthesizer = AVSpeechSynthesizer()

    // MARK: - API client
    private let apiClient = TextGenerationAPIClient()

    override init() {
        super.init()
        requestSpeechAuthorization()
    }

    // MARK: - Permissions

    private func requestSpeechAuthorization() {
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            guard let self else { return }
            Task { @MainActor in
                switch status {
                case .authorized:
                    break // всё ок
                case .denied:
                    self.errorMessage = "Speech recognition permission denied."
                case .restricted, .notDetermined:
                    self.errorMessage = "Speech recognition is not available."
                @unknown default:
                    self.errorMessage = "Unknown speech recognition status."
                }
            }
        }
    }

    // MARK: - Public API for View
    func toggleRecording() {
        if isRecording {
            stopRecording()
        } else {
            startRecording()
        }
    }

    /// Нажали и держим кнопку
    func beginRecordingHold() {
        if !isRecording {
            startRecording()
        }
    }

    /// Отпустили кнопку — стоп и сразу отправляем
    func endRecordingHold() {
        if isRecording {
            stopRecording()
        }
    }

    // MARK: - Speech recording

    private func startRecording() {
        errorMessage = nil
        recognizedText = ""

        // Останавливаем старую задачу, если есть
        recognitionTask?.cancel()
        recognitionTask = nil

        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.record, mode: .measurement, options: [.duckOthers])
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            errorMessage = "Audio session error: \(error.localizedDescription)"
            return
        }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest else {
            errorMessage = "Unable to create recognition request."
            return
        }

        recognitionRequest.shouldReportPartialResults = true

        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            errorMessage = "Speech recognizer is not available."
            return
        }

        let inputNode = audioEngine.inputNode

        recognitionTask = recognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
            guard let self else { return }

            if let result {
                Task { @MainActor in
                    self.recognizedText = result.bestTranscription.formattedString
                }

                if result.isFinal {
                    Task { @MainActor in
                        self.stopRecording()
                        self.sendToServerAndSpeak()
                    }
                }
            }

            if let error {
                Task { @MainActor in
                    self.errorMessage = "Recognition error: \(error.localizedDescription)"
                    self.stopRecording()
                }
            }
        }

        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.removeTap(onBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }

        do {
            audioEngine.prepare()
            try audioEngine.start()
            isRecording = true
        } catch {
            errorMessage = "Audio engine start error: \(error.localizedDescription)"
        }
    }

    private func stopRecording() {
        if audioEngine.isRunning {
            audioEngine.stop()
            recognitionRequest?.endAudio()
            audioEngine.inputNode.removeTap(onBus: 0)
        }
        isRecording = false

        // 👇 деактивируем аудио-сессию записи
        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            print("Audio session deactivation error: \(error)")
        }
    }

    // MARK: - Networking + TTS

    private func sendToServerAndSpeak() {
        let text = recognizedText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            return
        }

        Task {
            // включаем индикатор загрузки
            await MainActor.run {
                self.isWaitingForResponse = true
            }

            do {
                let responseText = try await apiClient.generateText(from: text)
                await MainActor.run {
                    self.generatedText = responseText
                    self.speak(text: responseText)
                }
            } catch {
                await MainActor.run {
                    if let urlError = error as? URLError {
                        print("URLError code:", urlError.code)
                    } else {
                        print("Other error:", error)
                    }
                    self.errorMessage = "API error: \(error.localizedDescription)"
                }
            }

            // выключаем индикатор загрузки
            await MainActor.run {
                self.isWaitingForResponse = false
            }
        }
    }

    private func speak(text: String) {
        print(text)

        let audioSession = AVAudioSession.sharedInstance()
        do {
            // 👇 включаем режим воспроизведения (можно .playback или .playAndRecord)
            try audioSession.setCategory(.playback, mode: .default, options: [.duckOthers])
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            print("Audio session playback error: \(error)")
        }

        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        speechSynthesizer.speak(utterance)
    }
}
