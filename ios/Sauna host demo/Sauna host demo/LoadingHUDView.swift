import SwiftUI

struct LoadingHUDView: View {
    @State private var animate = false

    var body: some View {
        ZStack {
            // полупрозрачное затемнение
            Color.black.opacity(0.35)
                .ignoresSafeArea()

            // "пузырьки" как в Siri
            VStack(spacing: 16) {
                ZStack {
                    ForEach(0..<3) { i in
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [
                                        Color.cyan,
                                        Color.blue,
                                        Color.purple
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 26, height: 26)
                            .scaleEffect(animate ? 1.0 : 0.5)
                            .opacity(animate ? 1.0 : 0.4)
                            .offset(x: CGFloat(i - 1) * 32)
                            .animation(
                                .easeInOut(duration: 0.7)
                                    .repeatForever(autoreverses: true)
                                    .delay(Double(i) * 0.15),
                                value: animate
                            )
                    }
                }

                Text("Processing your command…")
                    .font(.subheadline.weight(.medium))
                    .foregroundColor(.white.opacity(0.9))
            }
            .padding(.horizontal, 32)
            .padding(.vertical, 20)
            .background(
                RoundedRectangle(cornerRadius: 24)
                    .fill(Color.black.opacity(0.7))
                    .blur(radius: 0.5)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 24)
                    .stroke(Color.white.opacity(0.25), lineWidth: 1)
            )
            .shadow(color: Color.black.opacity(0.6), radius: 18, x: 0, y: 10)
        }
        .onAppear {
            animate = true
        }
    }
}

#Preview {
    ZStack {
        Color.black.ignoresSafeArea()
        LoadingHUDView()
    }
}
