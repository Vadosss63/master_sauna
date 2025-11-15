//
//  ContentView.swift
//  Sauna host demo
//
//  Created by Timur Lavrukhin on 15.11.2025.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = VoiceAssistantViewModel()

    @State private var bgRotation: Double = 0
    @State private var pulseAnimation: Bool = false

    var body: some View {
        ZStack {
            // Анимированный фон
            AnimatedGradientBackground(angle: bgRotation)
                .ignoresSafeArea()
                .onAppear {
                    withAnimation(.linear(duration: 30).repeatForever(autoreverses: false)) {
                        bgRotation = 360
                    }
                }

            VStack(spacing: 24) {
                Spacer().frame(height: 40)

                GlassCard(
                    title: "You said",
                    subtitle: "Input",
                    text: viewModel.recognizedText,
                    placeholder: "Tap the mic and start speaking…"
                )

                GlassCard(
                    title: "Assistant",
                    subtitle: "Response",
                    text: viewModel.generatedText,
                    placeholder: "Generated answer will appear here…"
                )

                Spacer()

                RecordButton(
                    isRecording: viewModel.isRecording,
                    pulseAnimation: $pulseAnimation
                ) { isPressing in
                    if isPressing {
                        // палец опустили — начинаем запись
                        viewModel.beginRecordingHold()
                    } else {
                        // палец отпустили — стоп и отправка на сервер
                        viewModel.endRecordingHold()
                    }
                }
                .padding(.bottom, 32)

                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundColor(.red.opacity(0.9))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                Spacer().frame(height: 16)
            }
            .padding(.horizontal, 20)

            // 👇 HUD поверх всего, пока ждём ответ
            if viewModel.isWaitingForResponse {
                LoadingHUDView()
                    .transition(.opacity)
                    .zIndex(1)
            }
        }
    }
}

struct AnimatedGradientBackground: View {
    let angle: Double

    var body: some View {
        ZStack {
            RadialGradient(
                colors: [
                    Color.black,
                    Color(red: 0.05, green: 0.05, blue: 0.1)
                ],
                center: .center,
                startRadius: 2,
                endRadius: 600
            )

            AngularGradient(
                gradient: Gradient(colors: [
                    Color.purple,
                    Color.blue,
                    Color.cyan,
                    Color.indigo,
                    Color.pink,
                    Color.purple
                ]),
                center: .center,
                angle: .degrees(angle)
            )
            .blur(radius: 80)
            .opacity(0.7)
        }
    }
}

struct GlassCard: View {
    let title: String
    let subtitle: String
    let text: String
    let placeholder: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.headline)
                        .foregroundColor(.white)

                    Text(subtitle.uppercased())
                        .font(.caption2)
                        .tracking(1.5)
                        .foregroundColor(.white.opacity(0.6))
                }

                Spacer()
            }

            // Поле для текста — выглядит как “input field”
            ZStack(alignment: .topLeading) {
                if text.isEmpty {
                    Text(placeholder)
                        .foregroundColor(.white.opacity(0.35))
                        .font(.subheadline)
                        .padding(.vertical, 4)
                }

                ScrollView {
                    Text(text)
                        .foregroundColor(.white)
                        .font(.subheadline)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 4)
                }
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 18)
                    .fill(Color.white.opacity(0.06))
            )
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 24)
                .fill(Color.white.opacity(0.08))
                .background(
                    RoundedRectangle(cornerRadius: 24)
                        .strokeBorder(
                            LinearGradient(
                                colors: [
                                    Color.white.opacity(0.4),
                                    Color.white.opacity(0.1)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
                .shadow(color: Color.black.opacity(0.5), radius: 20, x: 0, y: 12)
        )
    }
}

struct RecordButton: View {
    let isRecording: Bool
    @Binding var pulseAnimation: Bool
    let onPressChanged: (Bool) -> Void   // true = нажали, false = отпустили

    var body: some View {
        Button(action: {}) {              // action больше не используем
            ZStack {
                // Внешние пульсирующие кольца
                if isRecording {
                    Circle()
                        .stroke(Color.white.opacity(0.4), lineWidth: 4)
                        .frame(width: 170, height: 170)
                        .scaleEffect(pulseAnimation ? 1.2 : 0.9)
                        .opacity(pulseAnimation ? 0.0 : 0.6)
                        .animation(
                            .easeOut(duration: 1.2)
                                .repeatForever(autoreverses: false),
                            value: pulseAnimation
                        )
                }

                // Основной круг
                Circle()
                    .fill(
                        LinearGradient(
                            colors: isRecording
                            ? [Color.red, Color.orange]
                            : [Color.blue, Color.cyan],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 130, height: 130)
                    .shadow(color: Color.black.opacity(0.6), radius: 20, x: 0, y: 14)
                    .overlay(
                        Circle()
                            .strokeBorder(Color.white.opacity(0.7), lineWidth: 3)
                    )
                    .overlay(
                        Circle()
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        Color.white.opacity(0.8),
                                        Color.white.opacity(0.1)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 1.5
                            )
                            .blur(radius: 0.5)
                    )

                // Иконка микрофона / волны
                Image(systemName: isRecording ? "waveform" : "mic.fill")
                    .font(.system(size: 44, weight: .bold))
                    .foregroundColor(.white)
                    .shadow(color: Color.black.opacity(0.7), radius: 10, x: 0, y: 4)
            }
        }
        .buttonStyle(.plain)
        // Реакция на удержание: minimumDuration = 0 → срабатывает сразу при касании
        .onLongPressGesture(
            minimumDuration: 0,
            maximumDistance: 50,
            pressing: { isPressing in
                onPressChanged(isPressing)
            },
            perform: { }
        )
        .onChange(of: isRecording) { newValue in
            if newValue {
                pulseAnimation = true
            } else {
                pulseAnimation = false
            }
        }
    }
}



#Preview {
    ContentView()
}
