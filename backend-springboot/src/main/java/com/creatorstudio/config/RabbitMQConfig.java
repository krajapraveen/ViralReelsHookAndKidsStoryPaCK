package com.creatorstudio.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    public static final String EXCHANGE = "gen.exchange";
    public static final String STORY_REQUEST_QUEUE = "story.request";
    public static final String STORY_RESULT_QUEUE = "story.result";
    public static final String STORY_REQUEST_ROUTING_KEY = "story.request";
    public static final String STORY_RESULT_ROUTING_KEY = "story.result";

    @Bean
    public DirectExchange exchange() {
        return new DirectExchange(EXCHANGE);
    }

    @Bean
    public Queue storyRequestQueue() {
        return new Queue(STORY_REQUEST_QUEUE, true);
    }

    @Bean
    public Queue storyResultQueue() {
        return new Queue(STORY_RESULT_QUEUE, true);
    }

    @Bean
    public Binding storyRequestBinding(Queue storyRequestQueue, DirectExchange exchange) {
        return BindingBuilder.bind(storyRequestQueue).to(exchange).with(STORY_REQUEST_ROUTING_KEY);
    }

    @Bean
    public Binding storyResultBinding(Queue storyResultQueue, DirectExchange exchange) {
        return BindingBuilder.bind(storyResultQueue).to(exchange).with(STORY_RESULT_ROUTING_KEY);
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        return template;
    }
}