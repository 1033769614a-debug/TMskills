#!/usr/bin/env swift
import Foundation
import ImageIO
import Vision

guard CommandLine.arguments.count == 3 else {
    FileHandle.standardError.write(
        Data("usage: ocr_frames_vision.swift IMAGE_DIR OUTPUT_JSON\n".utf8)
    )
    exit(2)
}

let imageDirectory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let fileManager = FileManager.default

let imageURLs = try fileManager.contentsOfDirectory(
    at: imageDirectory,
    includingPropertiesForKeys: nil,
    options: [.skipsHiddenFiles]
).filter { ["jpg", "jpeg", "png"].contains($0.pathExtension.lowercased()) }
 .sorted { $0.lastPathComponent < $1.lastPathComponent }

var imageRecords: [[String: Any]] = []

for imageURL in imageURLs {
    guard
        let source = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
        let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else {
        imageRecords.append([
            "file": imageURL.lastPathComponent,
            "error": "image_decode_failed",
        ])
        continue
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-US", "zh-Hans"]
    request.minimumTextHeight = 0.005

    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])
    let observations = request.results ?? []
    let lines: [[String: Any]] = observations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return [
            "text": candidate.string,
            "confidence": Double(candidate.confidence),
            "bbox": [
                "x": Double(box.origin.x),
                "y": Double(box.origin.y),
                "width": Double(box.size.width),
                "height": Double(box.size.height),
            ],
        ]
    }
    imageRecords.append([
        "file": imageURL.lastPathComponent,
        "lines": lines,
    ])
}

let payload: [String: Any] = [
    "schema_version": 1,
    "engine": "macOS Vision VNRecognizeTextRequest",
    "image_count": imageRecords.count,
    "images": imageRecords,
]
let data = try JSONSerialization.data(
    withJSONObject: payload,
    options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
)
try fileManager.createDirectory(
    at: outputURL.deletingLastPathComponent(),
    withIntermediateDirectories: true
)
try data.write(to: outputURL, options: .atomic)
print("images=\(imageRecords.count)")
print("output=\(outputURL.path)")
