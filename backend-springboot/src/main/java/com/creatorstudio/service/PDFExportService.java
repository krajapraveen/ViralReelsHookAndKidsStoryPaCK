package com.creatorstudio.service;

import com.itextpdf.kernel.colors.ColorConstants;
import com.itextpdf.kernel.colors.DeviceRgb;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.kernel.pdf.canvas.PdfCanvas;
import com.itextpdf.kernel.pdf.extgstate.PdfExtGState;
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

    public byte[] generateStoryPDF(Map<String, Object> storyData, boolean isFreeTier) {
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            PdfWriter writer = new PdfWriter(baos);
            PdfDocument pdf = new PdfDocument(writer);
            Document document = new Document(pdf);

            // Colors
            DeviceRgb primaryColor = new DeviceRgb(99, 102, 241); // Indigo
            DeviceRgb purpleColor = new DeviceRgb(139, 92, 246); // Purple

            // Free tier watermark banner at top
            if (isFreeTier) {
                Paragraph watermarkBanner = new Paragraph("⚡ MADE WITH CREATORSTUDIO AI - FREE TIER | Upgrade to remove watermark")
                        .setFontSize(10)
                        .setBold()
                        .setFontColor(ColorConstants.WHITE)
                        .setBackgroundColor(purpleColor)
                        .setTextAlignment(TextAlignment.CENTER)
                        .setPadding(8)
                        .setMarginBottom(15);
                document.add(watermarkBanner);
            }

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
                        .add(new Text("Synopsis: ").setBold().setFontColor(purpleColor))
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
                            .setFontColor(purpleColor)
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

            // Free tier footer watermark
            if (isFreeTier) {
                Paragraph footerWatermark = new Paragraph("\n\n⚡ This content was generated with CreatorStudio AI (Free Tier)\nUpgrade your subscription to remove watermarks: creatorstudio.ai/pricing")
                        .setFontSize(9)
                        .setItalic()
                        .setFontColor(purpleColor)
                        .setTextAlignment(TextAlignment.CENTER)
                        .setMarginTop(30);
                document.add(footerWatermark);
            }

            document.close();
            return baos.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate PDF: " + e.getMessage());
        }
    }
    
    // Backward compatible method
    public byte[] generateStoryPDF(Map<String, Object> storyData) {
        return generateStoryPDF(storyData, true); // Default to free tier for safety
    }
}
