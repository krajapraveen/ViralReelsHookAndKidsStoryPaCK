package com.creatorstudio.service;

import com.itextpdf.kernel.colors.ColorConstants;
import com.itextpdf.kernel.colors.DeviceRgb;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.element.Paragraph;
import com.itextpdf.layout.element.Text;
import com.itextpdf.layout.properties.TextAlignment;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Map;

@Service
public class PDFExportService {

    public byte[] generateStoryPDF(Map<String, Object> storyData) {
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            PdfWriter writer = new PdfWriter(baos);
            PdfDocument pdf = new PdfDocument(writer);
            Document document = new Document(pdf);

            // Colors
            DeviceRgb primaryColor = new DeviceRgb(99, 102, 241); // Indigo
            DeviceRgb secondaryColor = new DeviceRgb(249, 115, 22); // Orange

            // Title
            String title = (String) storyData.get("title");
            Paragraph titlePara = new Paragraph(title)
                    .setFontSize(24)
                    .setBold()
                    .setFontColor(primaryColor)
                    .setTextAlignment(TextAlignment.CENTER)
                    .setMarginBottom(10);
            document.add(titlePara);

            // Branding
            Paragraph branding = new Paragraph("Generated with CreatorStudio AI")
                    .setFontSize(10)
                    .setItalic()
                    .setFontColor(ColorConstants.GRAY)
                    .setTextAlignment(TextAlignment.CENTER)
                    .setMarginBottom(20);
            document.add(branding);

            // Synopsis
            String synopsis = (String) storyData.get("synopsis");
            if (synopsis != null) {
                Paragraph synopsisPara = new Paragraph()
                        .add(new Text("Synopsis: ").setBold().setFontColor(secondaryColor))
                        .add(synopsis)
                        .setMarginBottom(15);
                document.add(synopsisPara);
            }

            // Characters
            List<Map<String, Object>> characters = (List<Map<String, Object>>) storyData.get("characters");
            if (characters != null && !characters.isEmpty()) {
                Paragraph charactersTitle = new Paragraph("Characters")
                        .setFontSize(16)
                        .setBold()
                        .setFontColor(primaryColor)
                        .setMarginTop(10)
                        .setMarginBottom(10);
                document.add(charactersTitle);

                for (Map<String, Object> character : characters) {
                    Paragraph charPara = new Paragraph()
                            .add(new Text(character.get("name") + ": ").setBold())
                            .add((String) character.get("description"))
                            .setMarginBottom(5);
                    document.add(charPara);
                }
            }

            // Scenes
            List<Map<String, Object>> scenes = (List<Map<String, Object>>) storyData.get("scenes");
            if (scenes != null && !scenes.isEmpty()) {
                Paragraph scenesTitle = new Paragraph("Scenes")
                        .setFontSize(16)
                        .setBold()
                        .setFontColor(primaryColor)
                        .setMarginTop(15)
                        .setMarginBottom(10);
                document.add(scenesTitle);

                for (Map<String, Object> scene : scenes) {
                    Integer sceneNum = (Integer) scene.get("scene_number");
                    Paragraph sceneTitle = new Paragraph("Scene " + sceneNum)
                            .setFontSize(14)
                            .setBold()
                            .setFontColor(secondaryColor)
                            .setMarginTop(10)
                            .setMarginBottom(5);
                    document.add(sceneTitle);

                    if (scene.get("shot_type") != null) {
                        document.add(new Paragraph("Shot: " + scene.get("shot_type"))
                                .setFontSize(10)
                                .setItalic()
                                .setMarginBottom(5));
                    }

                    if (scene.get("visual_description") != null) {
                        document.add(new Paragraph()
                                .add(new Text("Visual: ").setBold())
                                .add((String) scene.get("visual_description"))
                                .setMarginBottom(5));
                    }

                    if (scene.get("narration") != null) {
                        document.add(new Paragraph()
                                .add(new Text("Narration: ").setBold())
                                .add((String) scene.get("narration"))
                                .setMarginBottom(5));
                    }

                    if (scene.get("image_prompt") != null) {
                        document.add(new Paragraph()
                                .add(new Text("Image Prompt: ").setBold().setFontSize(9))
                                .add(new Text((String) scene.get("image_prompt")).setFontSize(9))
                                .setMarginBottom(10)
                                .setBackgroundColor(new DeviceRgb(245, 245, 245)));
                    }
                }
            }

            // YouTube Optimization
            Map<String, Object> youtube = (Map<String, Object>) storyData.get("youtube");
            if (youtube != null) {
                Paragraph youtubeTitle = new Paragraph("YouTube Optimization")
                        .setFontSize(16)
                        .setBold()
                        .setFontColor(primaryColor)
                        .setMarginTop(15)
                        .setMarginBottom(10);
                document.add(youtubeTitle);

                if (youtube.get("title") != null) {
                    document.add(new Paragraph()
                            .add(new Text("Title: ").setBold())
                            .add((String) youtube.get("title"))
                            .setMarginBottom(5));
                }

                if (youtube.get("description") != null) {
                    document.add(new Paragraph()
                            .add(new Text("Description: ").setBold())
                            .add((String) youtube.get("description"))
                            .setMarginBottom(5));
                }

                List<String> tags = (List<String>) youtube.get("tags");
                if (tags != null && !tags.isEmpty()) {
                    document.add(new Paragraph()
                            .add(new Text("Tags: ").setBold())
                            .add(String.join(", ", tags))
                            .setMarginBottom(5));
                }
            }

            document.close();
            return baos.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate PDF: " + e.getMessage());
        }
    }
}
